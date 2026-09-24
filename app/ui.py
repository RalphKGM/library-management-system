from flask import abort, flash, g, redirect, render_template, request, session, url_for

from app.db import get_db
from app.sample_catalog import CATEGORIES
from app.security import require_role
from app.services.borrowing import borrow_copy, get_borrowing_history, return_copy
from app.services.helpers import calculate_progress
from app.services.media import add_copy, add_media, get_available_copies, update_media
from app.services.members import authenticate_librarian, authenticate_member, register_member
from app.services.reading import (
    add_bookmark, get_all_progress, get_bookmarks, get_progress,
    remove_bookmark, update_progress,
)


def _catalog():
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


def register_ui(app):
    @app.context_processor
    def catalog_globals():
        categories = list(CATEGORIES)
        for row in get_db().execute("SELECT DISTINCT category FROM media_item ORDER BY category"):
            if row["category"] not in categories:
                categories.append(row["category"])
        return {"categories": categories}

    @app.get("/")
    def browse():
        works = _catalog()
        query = request.args.get("q", "").strip().casefold()
        category = request.args.get("category", "").strip()
        sort = request.args.get("sort", "title")
        filtered = [
            work for work in works
            if (not query or query in work["title"].casefold()
                or query in work["author"].casefold()
                or query in work["category"].casefold())
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
        return redirect(url_for("work_detail", media_id=media_id))

    @app.post("/works/<int:media_id>/progress")
    @require_role("member")
    def save_progress(media_id):
        try:
            update_progress(g.user["id"], media_id,
                            _whole_number(request.form.get("position"), "position"),
                            request.form.get("status", ""))
            flash("Reading progress saved.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("work_detail", media_id=media_id))

    @app.post("/works/<int:media_id>/bookmarks")
    @require_role("member")
    def save_bookmark(media_id):
        try:
            add_bookmark(g.user["id"], media_id,
                         _whole_number(request.form.get("position"), "position"),
                         request.form.get("note", ""))
            flash("Bookmark saved.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("work_detail", media_id=media_id))

    @app.post("/bookmarks/<int:bookmark_id>/delete")
    @require_role("member")
    def delete_bookmark(bookmark_id):
        if remove_bookmark(g.user["id"], bookmark_id):
            flash("Bookmark removed.", "success")
        else:
            abort(404)
        return redirect(url_for("member"))

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
        return redirect(url_for("member"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if g.user:
            return redirect(url_for("member" if g.user["role"] == "member" else "librarian"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            role = request.form.get("role", "member")
            if role not in ("member", "librarian"):
                abort(400)
            try:
                user = (authenticate_member if role == "member" else authenticate_librarian)(username, password)
            except ValueError:
                user = None
            if user:
                session.clear()
                session["role"] = role
                session["user_id"] = user["member_id" if role == "member" else "librarian_id"]
                flash("Signed in successfully.", "success")
                return redirect(url_for("member" if role == "member" else "librarian"))
            flash("Incorrect username or password.", "error")
        return render_template("auth/login.html")

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
                return redirect(url_for("member"))
        return render_template("auth/register.html")

    @app.post("/logout")
    def logout():
        session.clear()
        flash("Signed out.", "success")
        return redirect(url_for("browse"))

    @app.get("/librarian")
    @require_role("librarian")
    def librarian():
        return render_template("librarian/index.html", works=_catalog())

    @app.route("/librarian/titles/new", methods=["GET", "POST"])
    @require_role("librarian")
    def librarian_add_title():
        if request.method == "POST":
            try:
                work = add_media(_media_data(request.form), g.user["id"])
            except ValueError as exc:
                flash(str(exc), "error")
            else:
                flash("Title added.", "success")
                return redirect(url_for("librarian_add_copy", media_id=work["media_id"]))
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
                add_copy(media_id, request.form.get("accession", ""), g.user["id"])
            except ValueError as exc:
                flash(str(exc), "error")
            else:
                flash("Physical copy added.", "success")
                return redirect(url_for("librarian"))
        return render_template("librarian/copy_form.html", work=work)
