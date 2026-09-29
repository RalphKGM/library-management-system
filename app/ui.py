import re

from flask import abort, flash, g, redirect, render_template, request, session, url_for

from app.db import get_db
from app.sample_catalog import CATEGORIES
from app.security import require_role
from app.services.borrowing import borrow_copy, get_borrowing_history, return_copy
from app.services.helpers import calculate_progress
from app.services.media import add_copies, add_media, get_available_copies, update_media
from app.services.open_library import import_book, search_books
from app.services.notifications import clear_all, inbox, mark_read, unread_count
from app.services.members import authenticate_account, register_member
from app.services.reading import (
    add_bookmark, get_all_progress, get_bookmarks, get_progress,
    remove_bookmark, update_progress,
)


def _catalog():
    from app.services.media import get_media_genres_map
    genres_map = get_media_genres_map()
    rows = get_db().execute(
        "SELECT m.*, COUNT(c.copy_id) AS copies, "
        "COUNT(c.copy_id) - COUNT(b.borrowing_id) AS available "
        "FROM media_item m LEFT JOIN media_copy c ON c.media_id = m.media_id "
        "LEFT JOIN borrowing_record b ON b.copy_id = c.copy_id AND b.returned_at IS NULL "
        "GROUP BY m.media_id ORDER BY m.title COLLATE NOCASE, m.media_id"
    ).fetchall()
    works = []
    for row in rows:
        item = dict(row)
        item["slug"] = str(item["media_id"])
        item["length"] = (
            f'{item["total_units"]} {item["progress_unit"]}' +
            ("s" if item["total_units"] != 1 else "")
            if item["total_units"] else None
        )
        item["genres"] = genres_map.get(item["media_id"], [])
        works.append(item)
    return works


def _work(media_id):
    return next((item for item in _catalog() if item["media_id"] == media_id), None)


def _media_data(form):
    total = form.get("total_units", "").strip()
    if total:
        try:
            total = int(total)
        except ValueError as exc:
            raise ValueError("total pages or chapters must be a whole number") from exc
    else:
        total = None
    return {
        "title": form.get("title", ""),
        "author": form.get("author", ""),
        "category": form.get("category", ""),
        "volume": form.get("volume", ""),
        "progress_unit": form.get("progress_unit", "page"),
        "total_units": total,
        "description": form.get("description", "").strip(),
    }


def _whole_number(value, label):
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a whole number") from exc


def _return_to_work():
    target = request.form.get("next") or request.args.get("next", "")
    return target if re.fullmatch(r"/works/\d+", target) else None


def register_ui(app):
    @app.context_processor
    def catalog_globals():
        categories = list(CATEGORIES)
        for row in get_db().execute("SELECT DISTINCT category FROM media_item ORDER BY category"):
            if row["category"] not in categories:
                categories.append(row["category"])
        count = unread_count(g.user["role"], g.user["id"]) if g.user else 0
        items = inbox(g.user["role"], g.user["id"], 6) if g.user else []
        return {"categories": categories, "notification_count": count, "notification_items": items}

    @app.post("/notifications/read")
    @require_role(("member", "librarian"))
    def notifications_read_all():
        mark_read(g.user["role"], g.user["id"])
        return redirect(url_for("librarian" if g.user["role"] == "librarian" else "member"))

    @app.post("/notifications/clear")
    @require_role(("member", "librarian"))
    def notifications_clear_all():
        clear_all(g.user["role"], g.user["id"])
        return redirect(url_for("librarian" if g.user["role"] == "librarian" else "member"))

    @app.post("/notifications/<int:notification_id>/read")
    @require_role(("member", "librarian"))
    def notifications_read(notification_id):
        row = get_db().execute(
            "SELECT target FROM notification WHERE notification_id = ? "
            "AND recipient_role = ? AND recipient_id = ?",
            (notification_id, g.user["role"], g.user["id"]),
        ).fetchone()
        if row is None:
            abort(404)
        mark_read(g.user["role"], g.user["id"], notification_id)
        return redirect(row["target"])

    @app.get("/")
    def browse():
        if g.user and g.user["role"] == "librarian":
            return redirect(url_for("librarian"))
        works = _catalog()
        query = request.args.get("q", "").strip().casefold()
        category = request.args.get("category", "").strip()
        sort = request.args.get("sort", "title")
        filtered = [
            work for work in works
            if (not query
                or query in work["title"].casefold()
                or query in work["author"].casefold()
                or query in work["category"].casefold()
                or query in (work.get("description") or "").casefold()
                or any(query in g.casefold() for g in work.get("genres", [])))
            and (not category or work["category"] == category)
        ]
        if sort == "availability":
            filtered.sort(key=lambda work: (-work["available"], work["title"].casefold()))
        elif sort == "recent":
            filtered.sort(key=lambda work: (work["added_at"], work["media_id"]), reverse=True)
        else:
            filtered.sort(key=lambda work: work["title"].casefold())
        recent = sorted(works, key=lambda work: (work["added_at"], work["media_id"]), reverse=True)[:6]
        return render_template(
            "browse.html", works=works, filtered=filtered, query=request.args.get("q", "").strip(),
            active_category=category, sort=sort, featured=works[:4],
            popular=works[4:10], recent=recent,
        )

    @app.get("/works/<int:media_id>")
    def work_detail(media_id):
        if g.user and g.user["role"] == "librarian":
            return redirect(url_for("librarian_edit_title", media_id=media_id))
        work = _work(media_id)
        if work is None:
            abort(404)
        related = [w for w in _catalog() if w["category"] == work["category"] and w["media_id"] != media_id][:4]
        progress = get_progress(g.user["id"], media_id) if g.user and g.user["role"] == "member" else None
        bookmarks = get_bookmarks(g.user["id"], media_id) if g.user and g.user["role"] == "member" else []
        borrowed = bool(get_db().execute(
            "SELECT 1 FROM borrowing_record b JOIN media_copy c ON c.copy_id = b.copy_id "
            "WHERE b.member_id = ? AND c.media_id = ? AND b.returned_at IS NULL",
            (g.user["id"], media_id),
        ).fetchone()) if g.user and g.user["role"] == "member" else False
        return render_template("work_detail.html", work=work, related=related, progress=progress,
                               bookmarks=bookmarks, borrowed=borrowed)

    @app.post("/works/<int:media_id>/borrow")
    @require_role("member")
    def borrow(media_id):
        copies = get_available_copies(media_id)
        if not copies:
            flash("No copy is available right now.", "error")
        else:
            try:
                borrow_copy(g.user["id"], copies[0]["copy_id"])
                flash("Copy borrowed successfully.", "success")
            except ValueError as exc:
                flash(str(exc), "error")
        return redirect(url_for("work_detail", media_id=media_id, _anchor="borrow-panel"))

    @app.post("/works/<int:media_id>/progress")
    @require_role("member")
    def save_progress(media_id):
        try:
            position = _whole_number(request.form.get("position"), "position")
            work = _work(media_id)
            if work is None:
                abort(404)
            status = ("completed" if work["total_units"] and position == work["total_units"]
                      else "reading" if position > 0 else "not_started")
            update_progress(g.user["id"], media_id, position, status)
            flash("Reading progress saved.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("work_detail", media_id=media_id, _anchor="reader-tools"))

    @app.post("/works/<int:media_id>/bookmarks")
    @require_role("member")
    def save_bookmark(media_id):
        try:
            current = get_progress(g.user["id"], media_id)
            if current is None or current["current_position"] <= 0:
                raise ValueError("Save your reading position before bookmarking it.")
            add_bookmark(g.user["id"], media_id, current["current_position"])
            flash("Bookmark saved.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("work_detail", media_id=media_id, _anchor="reader-tools"))

    @app.post("/bookmarks/<int:bookmark_id>/delete")
    @require_role("member")
    def delete_bookmark(bookmark_id):
        if remove_bookmark(g.user["id"], bookmark_id):
            flash("Bookmark removed.", "success")
        else:
            abort(404)
        return redirect(url_for("member", _anchor="bookmarks"))

    @app.get("/member")
    @require_role("member")
    def member():
        history = get_borrowing_history(g.user["id"])
        progress = get_all_progress(g.user["id"])
        for entry in progress:
            entry["percent"] = calculate_progress(entry["current_position"], entry["total_units"])
        return render_template(
            "member.html", current=[entry for entry in history if entry["returned_at"] is None],
            history=[entry for entry in history if entry["returned_at"] is not None],
            progress=progress, bookmarks=get_bookmarks(g.user["id"]),
        )

    @app.post("/member/borrowings/<int:borrowing_id>/return")
    @require_role("member")
    def return_borrowing(borrowing_id):
        row = get_db().execute(
            "SELECT 1 FROM borrowing_record WHERE borrowing_id = ? AND member_id = ? AND returned_at IS NULL",
            (borrowing_id, g.user["id"]),
        ).fetchone()
        if row is None:
            abort(404)
        return_copy(borrowing_id)
        flash("Copy returned. Thank you.", "success")
        return redirect(url_for("member", _anchor="borrowings"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if g.user:
            return redirect(url_for("member" if g.user["role"] == "member" else "librarian"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            try:
                account = authenticate_account(username, password)
            except ValueError:
                account = None
            if account:
                role, user = account
                session.clear()
                session["role"] = role
                session["user_id"] = user["member_id" if role == "member" else "librarian_id"]
                flash("Signed in successfully.", "success")
                return redirect((_return_to_work() if role == "member" else None)
                                or url_for("member" if role == "member" else "librarian"))
            flash("Incorrect username or password.", "error")
        return render_template("auth/login.html", return_to_work=_return_to_work())

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if g.user:
            return redirect(url_for("member" if g.user["role"] == "member" else "librarian"))
        if request.method == "POST":
            try:
                if len(request.form.get("password", "")) < 8:
                    raise ValueError("Password must have at least 8 characters.")
                user = register_member(request.form.get("name", ""),
                                       request.form.get("username", ""),
                                       request.form.get("password", ""))
            except ValueError as exc:
                flash(str(exc), "error")
            else:
                session.clear()
                session["role"] = "member"
                session["user_id"] = user["member_id"]
                flash("Your membership is ready.", "success")
                return redirect(_return_to_work() or url_for("member"))
        return render_template("auth/register.html", return_to_work=_return_to_work())

    @app.post("/logout")
    def logout():
        session.clear()
        flash("Signed out.", "success")
        return redirect(url_for("browse"))

    @app.get("/settings")
    @require_role(("member", "librarian"))
    def settings():
        return render_template("settings.html")

    @app.get("/librarian")
    @require_role("librarian")
    def librarian():
        db = get_db()
        members = db.execute(
            "SELECT m.member_id, m.full_name, m.username, m.registered_at, "
            "COUNT(b.borrowing_id) AS borrowed "
            "FROM member m LEFT JOIN borrowing_record b ON b.member_id = m.member_id "
            "AND b.returned_at IS NULL "
            "GROUP BY m.member_id ORDER BY m.registered_at DESC, m.member_id DESC LIMIT 5"
        ).fetchall()
        totals = db.execute(
            "SELECT (SELECT COUNT(*) FROM member) AS members, "
            "(SELECT COUNT(*) FROM borrowing_record WHERE returned_at IS NULL) AS on_loan"
        ).fetchone()

        from app.services.analytics import (
            get_top_genres_borrowed,
            get_top_book_types_borrowed,
            get_book_borrowing_rankings,
            get_analytics_summary,
        )
        return render_template(
            "librarian/index.html",
            works=_catalog(),
            members=members,
            totals=totals,
            top_genres=get_top_genres_borrowed(limit=10),
            top_types=get_top_book_types_borrowed(),
            book_rankings=get_book_borrowing_rankings(limit=25),
            analytics_summary=get_analytics_summary(),
        )

    @app.get("/librarian/analytics")
    @require_role("librarian")
    def librarian_analytics():
        from app.services.analytics import (
            get_top_genres_borrowed,
            get_top_book_types_borrowed,
            get_book_borrowing_rankings,
            get_analytics_summary,
        )
        return render_template(
            "librarian/analytics.html",
            top_genres=get_top_genres_borrowed(limit=25),
            top_types=get_top_book_types_borrowed(),
            book_rankings=get_book_borrowing_rankings(limit=50),
            summary=get_analytics_summary(),
        )

    @app.get("/librarian/books")
    @require_role("librarian")
    def librarian_books():
        return render_template("librarian/books.html", works=_catalog())

    @app.get("/librarian/members")
    @require_role("librarian")
    def librarian_members():
        members = get_db().execute(
            "SELECT m.member_id, m.full_name, m.username, m.registered_at, "
            "COUNT(b.borrowing_id) AS on_loan FROM member m "
            "LEFT JOIN borrowing_record b ON b.member_id = m.member_id AND b.returned_at IS NULL "
            "GROUP BY m.member_id ORDER BY m.registered_at DESC, m.member_id DESC"
        ).fetchall()
        return render_template("librarian/members.html", members=members)

    @app.get("/librarian/loans")
    @require_role("librarian")
    def librarian_loans():
        loans = get_db().execute(
            "SELECT b.borrowing_id, b.borrowed_at, b.returned_at, "
            "m.full_name, i.title, c.accession_number "
            "FROM borrowing_record b JOIN member m ON m.member_id = b.member_id "
            "JOIN media_copy c ON c.copy_id = b.copy_id "
            "JOIN media_item i ON i.media_id = c.media_id "
            "ORDER BY (b.returned_at IS NULL) DESC, b.borrowed_at DESC, b.borrowing_id DESC"
        ).fetchall()
        return render_template("librarian/loans.html", loans=loans)

    @app.get("/librarian/copies")
    @require_role("librarian")
    def librarian_copies():
        copies = get_db().execute(
            "SELECT c.copy_id, c.media_id, c.accession_number, m.title, m.author, "
            "b.borrowing_id AS active_loan "
            "FROM media_copy c JOIN media_item m ON m.media_id = c.media_id "
            "LEFT JOIN borrowing_record b ON b.copy_id = c.copy_id AND b.returned_at IS NULL "
            "ORDER BY m.title COLLATE NOCASE, c.copy_id"
        ).fetchall()
        return render_template("librarian/copies.html", copies=copies)

    @app.get("/librarian/open-library")
    @require_role("librarian")
    def librarian_open_library():
        query = request.args.get("q", "").strip()
        provider = request.args.get("provider", "openlibrary").strip().lower()
        if provider not in ("openlibrary", "googlebooks"):
            provider = "openlibrary"
        results = []
        if query:
            try:
                if provider == "googlebooks":
                    from app.services.google_books import search_google_books
                    results = search_google_books(query)
                else:
                    results = search_books(query)
            except (ValueError, ConnectionError) as exc:
                flash(str(exc), "error")
        return render_template("librarian/open_library.html", query=query, results=results, provider=provider)

    @app.post("/librarian/open-library/import")
    @require_role("librarian")
    def librarian_import_open_library():
        try:
            work = import_book(request.form.get("import_token"), g.user["id"])
            add_copies(work["media_id"], 1, g.user["id"])
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("librarian_open_library"))
        flash("Book and first copy added.", "success")
        return redirect(url_for("librarian_books"))

    @app.route("/librarian/titles/new", methods=["GET", "POST"])
    @require_role("librarian")
    def librarian_add_title():
        if request.method == "POST":
            try:
                work = add_media(_media_data(request.form), g.user["id"])
                add_copies(work["media_id"], 1, g.user["id"])
            except ValueError as exc:
                flash(str(exc), "error")
            else:
                flash("Book and first copy added.", "success")
                return redirect(url_for("librarian_books"))
        return render_template("librarian/title_form.html", work=None, mode="Add")

    @app.route("/librarian/titles/<int:media_id>/edit", methods=["GET", "POST"])
    @require_role("librarian")
    def librarian_edit_title(media_id):
        work = _work(media_id)
        if work is None:
            abort(404)
        if request.method == "POST":
            try:
                update_media(media_id, _media_data(request.form), g.user["id"])
            except ValueError as exc:
                flash(str(exc), "error")
            else:
                flash("Title updated.", "success")
                return redirect(url_for("librarian"))
        return render_template("librarian/title_form.html", work=work, mode="Edit")

    @app.route("/librarian/titles/<int:media_id>/copies/new", methods=["GET", "POST"])
    @require_role("librarian")
    def librarian_add_copy(media_id):
        work = _work(media_id)
        if work is None:
            abort(404)
        if request.method == "POST":
            try:
                quantity = _whole_number(request.form.get("quantity"), "quantity")
                add_copies(media_id, quantity, g.user["id"])
            except ValueError as exc:
                flash(str(exc), "error")
            else:
                flash(f"{quantity} physical {'copy' if quantity == 1 else 'copies'} added.", "success")
                return redirect(url_for("librarian_copies"))
        return render_template("librarian/copy_form.html", work=work)
