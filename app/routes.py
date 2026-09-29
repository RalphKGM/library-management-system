import secrets

from flask import Blueprint, abort, g, jsonify, request, session
from werkzeug.exceptions import HTTPException

from app.db import get_db
from app.services.borrowing import borrow_copy, get_borrowing_history, return_copy
from app.services.media import add_copy, add_media, update_media
from app.services.open_library import import_book, search_books
from app.services.members import authenticate_account, register_member
from app.services.reading import (
    add_bookmark, get_bookmarks, get_progress, remove_bookmark, update_progress,
)

api = Blueprint("api", __name__, url_prefix="/api")


def _body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, "Expected a JSON object.")
    return data


def _role(role):
    if g.user is None:
        abort(401, "Sign in first.")
    if g.user["role"] != role:
        abort(403, "This page is for a different account type.")


@api.errorhandler(HTTPException)
def http_error(error):
    return jsonify(error=error.description), error.code


@api.errorhandler(ValueError)
def value_error(error):
    return jsonify(error=str(error)), 400


@api.get("/health")
def health():
    from flask import current_app
    try:
        db = get_db()
        book_count = db.execute("SELECT COUNT(*) FROM media_item").fetchone()[0]
        member_count = db.execute("SELECT COUNT(*) FROM member").fetchone()[0]
        staff_count = db.execute("SELECT COUNT(*) FROM librarian").fetchone()[0]
        loan_count = db.execute("SELECT COUNT(*) FROM borrowing_record").fetchone()[0]
        genre_count = db.execute("SELECT COUNT(*) FROM genre").fetchone()[0]
        return {
            "status": "ok",
            "server": "online",
            "database": "connected",
            "database_file": current_app.config.get("DATABASE"),
            "counts": {
                "books": book_count,
                "members": member_count,
                "staff": staff_count,
                "loans": loan_count,
                "genres": genre_count,
            },
        }
    except Exception as exc:
        return {"status": "error", "database": "disconnected", "error": str(exc)}, 500


@api.get("/session")
def session_info():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return {"user": g.user, "csrf_token": session["csrf_token"]}


@api.post("/members")
def create_member():
    data = _body()
    password = data.get("password", "")
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("password must have at least 8 characters")
    member = register_member(data.get("full_name"), data.get("username"), password)
    return jsonify(member), 201


@api.post("/session")
def create_session():
    data = _body()
    try:
        account = authenticate_account(data.get("username"), data.get("password"))
    except ValueError:
        account = None
    if not account:
        return jsonify(error="Incorrect username or password."), 401
    role, user = account
    session.clear()
    session["role"] = role
    session["user_id"] = user["member_id" if role == "member" else "librarian_id"]
    session["csrf_token"] = secrets.token_urlsafe(32)
    return {"user": {"id": session["user_id"], "role": role, "username": user["username"]},
            "csrf_token": session["csrf_token"]}


@api.delete("/session")
def delete_session():
    session.clear()
    return "", 204


@api.get("/open-library/search")
@api.get("/books/search")
def search_external_books():
    _role("librarian")
    provider = request.args.get("provider", "openlibrary").strip().lower()
    query = request.args.get("q", "")
    try:
        if provider == "googlebooks":
            from app.services.google_books import search_google_books
            return jsonify(search_google_books(query))
        return jsonify(search_books(query))
    except ConnectionError as exc:
        return jsonify(error=str(exc)), 503


@api.post("/open-library/import")
def import_open_library():
    _role("librarian")
    data = _body()
    return jsonify(import_book(data.get("import_token"), g.user["id"])), 201


@api.get("/media")
def list_media():
    from app.ui import _catalog

    query = request.args.get("q", "").casefold()
    category = request.args.get("category")
    return jsonify([
        item for item in _catalog()
        if (not query or query in item["title"].casefold() or query in item["author"].casefold())
        and (not category or item["category"] == category)
    ])


@api.get("/media/<int:media_id>")
def show_media(media_id):
    from app.ui import _work

    item = _work(media_id)
    if item is None:
        abort(404)
    return item


@api.post("/media")
def create_media():
    _role("librarian")
    return jsonify(add_media(_body(), g.user["id"])), 201


@api.patch("/media/<int:media_id>")
def edit_media(media_id):
    _role("librarian")
    item = update_media(media_id, _body(), g.user["id"])
    if item is None:
        abort(404)
    return item


@api.post("/media/<int:media_id>/copies")
def create_copy(media_id):
    _role("librarian")
    return jsonify(add_copy(media_id, _body().get("accession_number"), g.user["id"])), 201


@api.get("/borrowings")
def list_borrowings():
    _role("member")
    return jsonify(get_borrowing_history(g.user["id"]))


@api.post("/borrowings")
def create_borrowing():
    _role("member")
    return jsonify(borrow_copy(g.user["id"], _body().get("copy_id"))), 201


@api.post("/borrowings/<int:borrowing_id>/return")
def return_borrowing(borrowing_id):
    _role("member")
    row = get_db().execute(
        "SELECT 1 FROM borrowing_record WHERE borrowing_id = ? AND member_id = ? AND returned_at IS NULL",
        (borrowing_id, g.user["id"]),
    ).fetchone()
    if row is None:
        abort(404)
    return return_copy(borrowing_id)


@api.route("/media/<int:media_id>/progress", methods=["GET", "PUT"])
def reading_progress(media_id):
    _role("member")
    if request.method == "PUT":
        data = _body()
        return update_progress(g.user["id"], media_id, data.get("position"), data.get("status"))
    result = get_progress(g.user["id"], media_id)
    if result is None:
        abort(404)
    return result


@api.route("/media/<int:media_id>/bookmarks", methods=["GET", "POST"])
def bookmarks(media_id):
    _role("member")
    if request.method == "POST":
        data = _body()
        return jsonify(add_bookmark(g.user["id"], media_id, data.get("position"), data.get("note", ""))), 201
    return jsonify(get_bookmarks(g.user["id"], media_id))


@api.delete("/bookmarks/<int:bookmark_id>")
def delete_bookmark(bookmark_id):
    _role("member")
    if not remove_bookmark(g.user["id"], bookmark_id):
        abort(404)
    return "", 204


@api.get("/analytics/top-genres")
def api_top_genres():
    _role("librarian")
    from app.services.analytics import get_top_genres_borrowed
    return jsonify(get_top_genres_borrowed())


@api.get("/analytics/top-book-types")
def api_top_book_types():
    _role("librarian")
    from app.services.analytics import get_top_book_types_borrowed
    return jsonify(get_top_book_types_borrowed())


@api.get("/analytics/book-rankings")
def api_book_rankings():
    _role("librarian")
    from app.services.analytics import get_book_borrowing_rankings
    return jsonify(get_book_borrowing_rankings())


@api.route("/media/<int:media_id>/genres", methods=["GET", "PUT"])
def media_genres_route(media_id):
    from app.services.media import get_media_genres, set_media_genres
    if request.method == "PUT":
        _role("librarian")
        data = _body()
        genres = data.get("genres", [])
        return jsonify(set_media_genres(media_id, genres))
    return jsonify(get_media_genres(media_id))
