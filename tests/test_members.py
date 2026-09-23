import pytest
from app.services.members import (
    authenticate_member,
    get_member,
    get_member_by_username,
    is_librarian,
    register_member,
)


def test_register_member_success(app):
    with app.app_context():
        member = register_member("Alice Smith", "alicesmith", "secret123")
        assert member.member_id is not None
        assert member.full_name == "Alice Smith"
        assert member.username == "alicesmith"
        assert member.role == "member"
        assert member.password_hash != "secret123"
        assert "T" in member.registered_at  # ISO format timestamp


def test_register_librarian_success(app):
    with app.app_context():
        member = register_member("Bob Jones", "bobjones", "secret456", role="librarian")
        assert member.role == "librarian"
        assert is_librarian(member) is True


def test_register_member_invalid_role(app):
    with app.app_context():
        with pytest.raises(ValueError) as exc:
            register_member("Charlie", "charlie", "password", role="admin")
        assert "Invalid role" in str(exc.value)


@pytest.mark.parametrize(
    ("full_name", "username", "password", "error_msg"),
    [
        ("", "user1", "pass", "Full name cannot be empty."),
        ("   ", "user1", "pass", "Full name cannot be empty."),
        ("User One", "", "pass", "Username cannot be empty."),
        ("User One", "   ", "pass", "Username cannot be empty."),
        ("User One", "user1", "", "Password cannot be empty."),
    ],
)
def test_register_member_validation_errors(app, full_name, username, password, error_msg):
    with app.app_context():
        with pytest.raises(ValueError) as exc:
            register_member(full_name, username, password)
        assert error_msg in str(exc.value)


def test_register_duplicate_username(app):
    with app.app_context():
        register_member("User One", "uniqueuser", "password123")
        with pytest.raises(ValueError) as exc:
            register_member("User Two", "uniqueuser", "anotherpass")
        assert "already taken" in str(exc.value)


def test_authenticate_member(app):
    with app.app_context():
        register_member("Jane Doe", "janedoe", "mypassword")

        # Successful authentication
        auth_member = authenticate_member("janedoe", "mypassword")
        assert auth_member is not None
        assert auth_member.username == "janedoe"
        assert auth_member.full_name == "Jane Doe"

        # Incorrect password
        assert authenticate_member("janedoe", "wrongpassword") is None

        # Unknown username
        assert authenticate_member("nonexistent", "mypassword") is None

        # Empty inputs
        assert authenticate_member("", "mypassword") is None
        assert authenticate_member("janedoe", "") is None


def test_get_member_and_lookup(app):
    with app.app_context():
        created = register_member("Sam Lee", "samlee", "samspass")

        found_by_id = get_member(created.member_id)
        assert found_by_id is not None
        assert found_by_id.username == "samlee"

        assert get_member(99999) is None

        found_by_user = get_member_by_username("samlee")
        assert found_by_user is not None
        assert found_by_user.member_id == created.member_id

        assert get_member_by_username("nouser") is None
        assert get_member_by_username("") is None


def test_is_librarian_check(app):
    with app.app_context():
        member = register_member("Borrower User", "borrower1", "pass", role="member")
        librarian = register_member("Staff User", "staff1", "pass", role="librarian")

        assert is_librarian(member) is False
        assert is_librarian(librarian) is True
        assert is_librarian(None) is False


def test_member_to_dict(app):
    with app.app_context():
        member = register_member("Display User", "displayuser", "pass")
        data = member.to_dict()
        assert "password_hash" not in data
        assert data["username"] == "displayuser"
        assert data["role"] == "member"

        data_with_hash = member.to_dict(include_password=True)
        assert "password_hash" in data_with_hash
