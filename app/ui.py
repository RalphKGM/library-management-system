from flask import abort, redirect, render_template, request, url_for

from app.db import get_db
from app.demo_catalog import CATEGORIES, DEMO_WORKS


def _catalog():
    db = get_db()
    rows = db.execute(
        "SELECT m.*, COUNT(c.copy_id) AS copies, "
        "COUNT(c.copy_id) - COUNT(b.borrowing_id) AS available "
        "FROM media_item m "
        "LEFT JOIN media_copy c ON c.media_id = m.media_id "
        "LEFT JOIN borrowing_record b ON b.copy_id = c.copy_id AND b.returned_at IS NULL "
        "GROUP BY m.media_id ORDER BY m.title, m.media_id"
    ).fetchall()
    works = []
    for row in rows:
        item = dict(row)
        item.update(
            slug=str(row["media_id"]),
            description="This title is part of the library collection.",
            length=f'{row["total_units"]} {row["progress_unit"]}s' if row["total_units"] else None,
            cover="catalog-placeholder.svg",
        )
        works.append(item)
    return works


def _display_catalog():
    works = _catalog()
    return (works, False) if works else (DEMO_WORKS, True)


def _work(slug):
    works, demo = _display_catalog()
    return next((work for work in works if work["slug"] == slug), None), works, demo


def register_ui(app):
    @app.context_processor
    def catalog_globals():
        return {"categories": CATEGORIES}

    @app.get("/")
    def browse():
        works, demo = _display_catalog()
        query = request.args.get("q", "").strip()
        category = request.args.get("category", "").strip()
        sort = request.args.get("sort", "title")
        filtered = [
            work for work in works
            if (not query or query.casefold() in work["title"].casefold()
                or query.casefold() in work["author"].casefold()
                or query.casefold() in work["category"].casefold())
            and (not category or work["category"] == category)
        ]
        if sort == "availability":
            filtered.sort(key=lambda work: (-work["available"], work["title"]))
        elif sort == "recent":
            filtered.sort(key=lambda work: work["slug"], reverse=True)
        else:
            filtered.sort(key=lambda work: work["title"])
        return render_template(
            "browse.html", works=works, filtered=filtered, query=query,
            active_category=category, sort=sort, demo=demo,
            featured=works[:4] if not demo else [w for w in works if w["featured"]],
            popular=works[4:10] if not demo else [w for w in works if w["popular"]][:6],
            recent=list(reversed(works[-6:])) if not demo else [w for w in works if w["recent"]][:6],
        )

    @app.get("/works/<slug>")
    def work_detail(slug):
        work, works, demo = _work(slug)
        if work is None:
            abort(404)
        related = [w for w in works if w["category"] == work["category"] and w["slug"] != slug][:4]
        return render_template("work_detail.html", work=work, related=related, demo=demo)

    @app.get("/member")
    def member():
        return render_template("member.html", current=[], progress=[], bookmarks=[], history=[])

    @app.get("/login")
    def login():
        return render_template("auth/login.html", errors={})

    @app.get("/register")
    def register():
        return render_template("auth/register.html", errors={})

    @app.get("/librarian")
    def librarian():
        return render_template("librarian/index.html", works=_catalog())

    @app.get("/librarian/titles/new")
    def librarian_add_title():
        return render_template("librarian/title_form.html", work=None, mode="Add")

    @app.get("/librarian/titles/<slug>/edit")
    def librarian_edit_title(slug):
        work, _, demo = _work(slug)
        if work is None or demo:
            abort(404)
        return render_template("librarian/title_form.html", work=work, mode="Edit")

    @app.get("/librarian/titles/<slug>/copies/new")
    def librarian_add_copy(slug):
        work, _, demo = _work(slug)
        if work is None or demo:
            abort(404)
        return render_template("librarian/copy_form.html", work=work)
