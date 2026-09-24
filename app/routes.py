import secrets

from flask import Blueprint, abort, g, jsonify, request, session
from werkzeug.exceptions import HTTPException

from app.db import get_db
from app.services.borrowing import borrow_copy, get_borrowing_history, return_copy
from app.services.media import add_copy, add_media, update_media
from app.services.members import authenticate_librarian, authenticate_member, register_member
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
    return {"status": "ok"}


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
    role = data.get("role", "member")
    if role not in ("member", "librarian"):
        raise ValueError("invalid account type")
    try:
        user = (authenticate_member if role == "member" else authenticate_librarian)(
            data.get("username"), data.get("password"),
        )
    except ValueError:
        user = None
    if not user:
        return jsonify(error="Incorrect username or password."), 401
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
