# Walkthrough: Membership, Authentication, and Librarian Permissions (Step 2)

We have completed the implementation of **Step 2 (Authentication & Membership)** along with the foundational **SQLite Database Layer** for the Entertainment Media Library Management System.

---

## 1. Summary of Changes

### Database Layer
- **[app/schema.sql](file:///c:/Users/GERARD%20CRUZ/OneDrive/Desktop/library-management-system/app/schema.sql)**:
  - Added `role TEXT NOT NULL DEFAULT 'member' CHECK(role IN ('member', 'librarian'))` to the `member` table definition.
- **[app/db.py](file:///c:/Users/GERARD%20CRUZ/OneDrive/Desktop/library-management-system/app/db.py)**:
  - Implemented `get_db()` with request-scoped caching on `flask.g`, row factory set to `sqlite3.Row`, and foreign keys enforced via `PRAGMA foreign_keys = ON;`.
  - Implemented `close_db(error=None)` to automatically close active connections on context teardown.
  - Implemented `init_db()` to create instance directories and execute schema script.
  - Implemented `init_app(app)` registering `close_db` teardown and the `flask init-db` CLI command.
- **[app/__init__.py](file:///c:/Users/GERARD%20CRUZ/OneDrive/Desktop/library-management-system/app/__init__.py)**:
  - Configured default `SECRET_KEY` for session signing.
  - Registered `db.init_app(app)`.
  - Ensured instance directory creation.

### Data Models & Service Layer
- **[app/models.py](file:///c:/Users/GERARD%20CRUZ/OneDrive/Desktop/library-management-system/app/models.py)**:
  - Updated `Member` dataclass to include `role: str = "member"`.
  - Added `to_dict(include_password=False)` helper method to safely serialize member profiles without leaking password hashes.
- **[app/services/members.py](file:///c:/Users/GERARD%20CRUZ/OneDrive/Desktop/library-management-system/app/services/members.py)**:
  - `register_member(full_name, username, password, role="member")`: Input validation, role validation, password hashing using `werkzeug.security.generate_password_hash`, ISO 8601 UTC timestamps, unique username constraint handling, and atomic database insertion.
  - `authenticate_member(username, password)`: Credential lookup and constant-time password verification using `werkzeug.security.check_password_hash`.
  - `get_member(member_id)`: Member lookup by primary key.
  - `get_member_by_username(username)`: Member lookup by unique username.
  - `is_librarian(member)`: Helper returning whether a member has librarian permissions.

### API Routes & Auth Middleware
- **[app/routes.py](file:///c:/Users/GERARD%20CRUZ/OneDrive/Desktop/library-management-system/app/routes.py)**:
  - Added `load_logged_in_user` running before every request to populate `flask.g.current_user` from the session.
  - Added `@login_required` decorator enforcing an active session (returns HTTP 401 if unauthenticated).
  - Added `@librarian_required` decorator enforcing librarian role (returns HTTP 403 if authenticated but not a librarian).
  - `POST /api/auth/register`: Endpoint for member & staff registration.
  - `POST /api/auth/login`: Endpoint for credentials verification and session creation.
  - `POST /api/auth/logout`: Endpoint for session clearing.
  - `GET /api/auth/me`: Authenticated endpoint returning current user profile.
  - `GET /api/auth/librarian-check`: Librarian-restricted endpoint for role verification.
  - `GET /api/members/<int:member_id>`: Member profile lookup by ID.

### Automated Tests & Dependencies
- **[requirements.txt](file:///c:/Users/GERARD%20CRUZ/OneDrive/Desktop/library-management-system/requirements.txt)**: Added `pytest>=8.0`.
- **[tests/conftest.py](file:///c:/Users/GERARD%20CRUZ/OneDrive/Desktop/library-management-system/tests/conftest.py)**: Pytest fixtures for temporary SQLite database, Flask app context, client, and CLI runner.
- **[tests/test_db.py](file:///c:/Users/GERARD%20CRUZ/OneDrive/Desktop/library-management-system/tests/test_db.py)**: Database connection lifecycle, table creation, foreign key enforcement, and `flask init-db` CLI test.
- **[tests/test_members.py](file:///c:/Users/GERARD%20CRUZ/OneDrive/Desktop/library-management-system/tests/test_members.py)**: Member registration, password hashing verification, duplicate username prevention, authentication verification, and librarian checks.
- **[tests/test_auth_routes.py](file:///c:/Users/GERARD%20CRUZ/OneDrive/Desktop/library-management-system/tests/test_auth_routes.py)**: HTTP endpoint tests for registration, login, logout, profile retrieval, and role-based access control.

---

## 2. Test Verification Results

All 25 automated tests passed:

```sh
.venv\Scripts\python -m pytest -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\GERARD CRUZ\OneDrive\Desktop\library-management-system
collected 25 items

tests/test_auth_routes.py::test_health_check PASSED                      [  4%]
tests/test_auth_routes.py::test_register_route_success PASSED            [  8%]
tests/test_auth_routes.py::test_register_route_missing_fields PASSED     [ 12%]
tests/test_auth_routes.py::test_register_route_invalid_json PASSED       [ 16%]
tests/test_auth_routes.py::test_register_route_duplicate_username PASSED [ 20%]
tests/test_auth_routes.py::test_login_and_session_management PASSED      [ 24%]
tests/test_auth_routes.py::test_get_member_profile_route PASSED          [ 28%]
tests/test_auth_routes.py::test_librarian_required_decorator PASSED      [ 32%]
tests/test_db.py::test_get_close_db PASSED                               [ 36%]
tests/test_db.py::test_foreign_keys_enabled PASSED                       [ 40%]
tests/test_db.py::test_tables_created PASSED                             [ 44%]
tests/test_db.py::test_init_db_command PASSED                            [ 48%]
tests/test_members.py::test_register_member_success PASSED               [ 52%]
tests/test_members.py::test_register_librarian_success PASSED            [ 56%]
tests/test_members.py::test_register_member_invalid_role PASSED          [ 60%]
tests/test_members.py::test_register_member_validation_errors[-user1-pass-Full name cannot be empty.] PASSED [ 64%]
tests/test_members.py::test_register_member_validation_errors[   -user1-pass-Full name cannot be empty.] PASSED [ 68%]
tests/test_members.py::test_register_member_validation_errors[User One--pass-Username cannot be empty.] PASSED [ 72%]
tests/test_members.py::test_register_member_validation_errors[User One-   -pass-Username cannot be empty.] PASSED [ 76%]
tests/test_members.py::test_register_member_validation_errors[User One-user1--Password cannot be empty.] PASSED [ 80%]
tests/test_members.py::test_register_duplicate_username PASSED           [ 84%]
tests/test_members.py::test_authenticate_member PASSED                   [ 88%]
tests/test_members.py::test_get_member_and_lookup PASSED                 [ 92%]
tests/test_members.py::test_is_librarian_check PASSED                    [ 96%]
tests/test_members.py::test_member_to_dict PASSED                        [100%]

============================= 25 passed in 10.66s =============================
```

### CLI Database Initialization
Tested and verified:
```sh
.venv\Scripts\python -m flask --app app init-db
# Output: Initialized the database.
```
Verified that `instance/library.sqlite3` was successfully generated with all tables.
