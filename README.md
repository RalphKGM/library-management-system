# Entertainment Media Library Management System

Group 2 | Principles of Programming Languages

Backend starter for a member-based library of manga, comics, novels, magazines, and graphic novels. Registered members may borrow available copies without a borrowing fee. Reading progress and bookmarks are planned features.

## What is included

- Flask application factory, health endpoint, and explicit `init-db` command.
- SQLite database helpers and schema.
- Member registration and authentication with hashed passwords.
- Trusted librarian account creation and authentication.
- Librarian-gated catalog and physical-copy service functions.

Borrowing, reading progress, bookmarks, and feature routes remain planned. Service functions are Python APIs; no login sessions or HTTP permission checks are implemented yet.

## Run locally

Use Python 3.9 or newer. From this folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m flask --app app init-db
python -m flask --app app run --debug
```

On Windows, activate with `.venv\Scripts\activate` instead.

Check `http://127.0.0.1:5000/api/health`. It returns `{"status": "ok"}`. The root URL has no page because frontend work is left to the group. Debug mode is for local development only.

## Structure

```text
app/
  __init__.py         Flask setup
  routes.py           health route and future endpoint notes
  models.py           library record classes
  db.py               SQLite connection and initialization
  schema.sql          SQLite table definitions
  services/
    members.py        member and librarian services
    media.py          catalog and copy services
    borrowing.py      borrowing and return stubs
    reading.py        progress and bookmark stubs
    helpers.py        pure function stubs
tests/
  README.md           future test scenarios
requirements.txt
.gitignore
```

## Suggested implementation order

1. Database initialization, membership, authentication, and catalog services are implemented.
2. Implement borrowing and returns. Confirm membership and copy availability; prevent two active borrowings of the same copy atomically.
3. Implement reading progress, bookmarks, and pure helper functions.
4. Add Flask endpoints, validation, error responses, and tests. Connect your frontend when ready.

`Member` represents borrowers. Create a librarian account through the trusted `create_librarian` Python service during setup. Catalog mutations require a librarian ID. This service-level check does not replace authenticated HTTP sessions when routes are added. Dates are stored as ISO-formatted text in the proposed SQLite schema. Progress and bookmarks belong to a member and title, so they can remain after a copy is returned. No payment or financial transaction features are planned.

## Start your repository

Copy or extract this folder to your chosen project location, then run:

```sh
git init
git add .
git commit -m "Add library backend boilerplate"
```

Create an empty remote repository yourself, then follow its instructions to add the remote and push. No repository or remote has been created by this scaffold.

Reference: [Flask application factories](https://flask.palletsprojects.com/en/stable/patterns/appfactories/).
