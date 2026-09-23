from functools import wraps
from flask import Blueprint, g, jsonify, request, session

from .services.members import (
    authenticate_member,
    get_member,
    is_librarian,
    register_member,
)

api = Blueprint("api", __name__, url_prefix="/api")


@api.before_app_request
def load_logged_in_user():
    """Load the logged-in member into flask.g before handling any request."""
    member_id = session.get("member_id")
    if member_id is None:
        g.current_user = None
    else:
        g.current_user = get_member(member_id)


def login_required(view):
    """Decorator ensuring that an active authenticated session exists."""
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.current_user is None:
            return jsonify({"error": "Unauthorized. Please log in."}), 401
        return view(**kwargs)
    return wrapped_view


def librarian_required(view):
    """Decorator ensuring that the active user has librarian privileges."""
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.current_user is None:
            return jsonify({"error": "Unauthorized. Please log in."}), 401
        if not is_librarian(g.current_user):
            return jsonify({"error": "Forbidden. Librarian access required."}), 403
        return view(**kwargs)
    return wrapped_view


@api.get("/health")
def health():
    return {"status": "ok"}


@api.post("/auth/register")
def register():
    """Register a new member or librarian."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a valid JSON object."}), 400

    full_name = data.get("full_name")
    username = data.get("username")
    password = data.get("password")
    role = data.get("role", "member")

    if not full_name or not username or not password:
        return jsonify({"error": "Fields 'full_name', 'username', and 'password' are required."}), 400

    try:
        member = register_member(
            full_name=full_name,
            username=username,
            password=password,
            role=role,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "message": "Registration successful.",
        "member": member.to_dict(),
    }), 201


@api.post("/auth/login")
def login():
    """Authenticate member credentials and establish a session."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a valid JSON object."}), 400

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    member = authenticate_member(username, password)
    if member is None:
        return jsonify({"error": "Invalid username or password."}), 401

    session.clear()
    session["member_id"] = member.member_id
    session["username"] = member.username
    session["role"] = member.role

    return jsonify({
        "message": "Login successful.",
        "member": member.to_dict(),
    }), 200


@api.post("/auth/logout")
def logout():
    """Clear session data on logout."""
    session.clear()
    return jsonify({"message": "Logged out successfully."}), 200


@api.get("/auth/me")
@login_required
def get_current_user():
    """Return profile of the currently authenticated member."""
    return jsonify({"member": g.current_user.to_dict()}), 200


@api.get("/auth/librarian-check")
@librarian_required
def librarian_check():
    """Verify that current session belongs to a librarian."""
    return jsonify({
        "message": "Librarian access granted.",
        "member": g.current_user.to_dict(),
    }), 200


@api.get("/members/<int:member_id>")
@login_required
def get_member_profile(member_id: int):
    """Retrieve profile of a member by ID (login required)."""
    member = get_member(member_id)
    if member is None:
        return jsonify({"error": f"Member with id {member_id} not found."}), 404

    return jsonify({"member": member.to_dict()}), 200
