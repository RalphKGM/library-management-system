import secrets
from functools import wraps

from flask import abort, g, redirect, request, session, url_for

from app.db import get_db


def current_user():
    role = session.get("role")
    user_id = session.get("user_id")
    if role not in ("member", "librarian") or type(user_id) is not int:
        return None
    table = "member" if role == "member" else "librarian"
    column = f"{table}_id"
    row = get_db().execute(
        f"SELECT {column}, username FROM {table} WHERE {column} = ?", (user_id,)
    ).fetchone()
    return {"id": user_id, "role": role, "username": row["username"]} if row else None


def require_role(role):
    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                return redirect(url_for("login"))
            if g.user["role"] != role:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorate


def init_security(app):
    @app.before_request
    def load_identity():
        g.user = current_user()
        if session.get("user_id") and g.user is None:
            session.clear()
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.endpoint != "api.health":
            supplied = request.form.get("csrf_token", "") or request.headers.get("X-CSRF-Token", "")
            expected = session.get("csrf_token", "")
            if not expected or not secrets.compare_digest(supplied, expected):
                abort(400, "Invalid form token. Reload the page and try again.")

    @app.context_processor
    def inject_security():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return {"current_user": g.user, "csrf_token": session["csrf_token"]}
