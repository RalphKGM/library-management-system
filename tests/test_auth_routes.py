import json
from app.routes import api, librarian_required


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_register_route_success(client):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Test User",
            "username": "testuser",
            "password": "mypassword",
            "role": "member",
        },
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["message"] == "Registration successful."
    assert data["member"]["username"] == "testuser"
    assert data["member"]["role"] == "member"
    assert "password_hash" not in data["member"]


def test_register_route_missing_fields(client):
    response = client.post(
        "/api/auth/register",
        json={"username": "incomplete"},
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_register_route_invalid_json(client):
    response = client.post(
        "/api/auth/register",
        data="not a json string",
        content_type="text/plain",
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_register_route_duplicate_username(client):
    payload = {
        "full_name": "First User",
        "username": "dupeuser",
        "password": "password123",
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already taken" in res2.get_json()["error"]


def test_login_and_session_management(client):
    # Register user
    client.post(
        "/api/auth/register",
        json={
            "full_name": "Session User",
            "username": "sessionuser",
            "password": "validpassword",
        },
    )

    # Login with missing fields
    bad_req = client.post("/api/auth/login", json={"username": "sessionuser"})
    assert bad_req.status_code == 400

    # Login with wrong password
    unauth = client.post(
        "/api/auth/login",
        json={"username": "sessionuser", "password": "wrongpassword"},
    )
    assert unauth.status_code == 401
    assert "Invalid username or password" in unauth.get_json()["error"]

    # Login with correct password
    login_res = client.post(
        "/api/auth/login",
        json={"username": "sessionuser", "password": "validpassword"},
    )
    assert login_res.status_code == 200
    assert login_res.get_json()["message"] == "Login successful."

    # Access /api/auth/me while logged in
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.get_json()["member"]["username"] == "sessionuser"

    # Logout
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200

    # Access /api/auth/me after logout -> 401 Unauthorized
    after_me_res = client.get("/api/auth/me")
    assert after_me_res.status_code == 401


def test_get_member_profile_route(client):
    # Register two users
    res1 = client.post(
        "/api/auth/register",
        json={"full_name": "User One", "username": "userone", "password": "pw"},
    )
    member1_id = res1.get_json()["member"]["member_id"]

    # Not logged in
    assert client.get(f"/api/members/{member1_id}").status_code == 401

    # Log in
    client.post("/api/auth/login", json={"username": "userone", "password": "pw"})

    # Fetch existing member
    res = client.get(f"/api/members/{member1_id}")
    assert res.status_code == 200
    assert res.get_json()["member"]["username"] == "userone"

    # Fetch non-existent member
    res_404 = client.get("/api/members/9999")
    assert res_404.status_code == 404


def test_librarian_required_decorator(client):
    # 1. Anonymous access -> 401
    anon_res = client.get("/api/auth/librarian-check")
    assert anon_res.status_code == 401

    # 2. Member (borrower) access -> 403 Forbidden
    client.post(
        "/api/auth/register",
        json={"full_name": "Borrower", "username": "borrower", "password": "pw", "role": "member"},
    )
    client.post("/api/auth/login", json={"username": "borrower", "password": "pw"})
    member_res = client.get("/api/auth/librarian-check")
    assert member_res.status_code == 403
    assert "Librarian access required" in member_res.get_json()["error"]

    # 3. Librarian access -> 200 OK
    client.post("/api/auth/logout")
    client.post(
        "/api/auth/register",
        json={"full_name": "Staff", "username": "staff", "password": "pw", "role": "librarian"},
    )
    client.post("/api/auth/login", json={"username": "staff", "password": "pw"})
    staff_res = client.get("/api/auth/librarian-check")
    assert staff_res.status_code == 200
    assert staff_res.get_json()["message"] == "Librarian access granted."
