# Entertainment Media Library Management System

Group 2 | Principles of Programming Languages

Backend starter for a member-based library of manga, comics, novels, magazines, and graphic novels. Registered members may borrow available copies without a borrowing fee. Reading progress and bookmarks are planned features.

## What is included

- A Flask application factory and `/api/health` endpoint.
- Simple Python record classes matching the proposed ERD.
- Function signatures for the group to implement.
- A SQLite schema starting point and database helper placeholders.
- Repository ignore rules and setup instructions.

This is a scaffold, not a working library system. Authentication, database operations, borrowing rules, validation, search, progress, and bookmarks are not implemented. Placeholder functions raise `NotImplementedError`. No frontend files, templates, styles, or scripts are included or modified.

## Run locally

Use Python 3.9 or newer. From this folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
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
  db.py               SQLite helper stubs
  schema.sql          proposed SQLite table definitions
  services/
    members.py        membership and login stubs
    media.py          catalog and copy stubs
    borrowing.py      borrowing and return stubs
    reading.py        progress and bookmark stubs
    helpers.py        pure function stubs
tests/
  README.md           future test scenarios
requirements.txt
.gitignore
```

## Suggested implementation order

1. Review `schema.sql`, implement `db.py`, and initialize the database.
2. Implement membership and authentication, including password hashing and librarian permissions.
3. Implement catalog and physical-copy management.
4. Implement borrowing and returns. Confirm membership and copy availability; prevent two active borrowings of the same copy atomically.
5. Implement reading progress, bookmarks, and pure helper functions.
6. Add Flask endpoints, validation, error responses, and tests. Connect your frontend when ready.

`Member` represents borrowers. Librarian authentication is intentionally left for implementation; no administrative account or access rule is preconfigured. Dates are stored as ISO-formatted text in the proposed SQLite schema. Progress and bookmarks belong to a member and title, so they can remain after a copy is returned. No payment or financial transaction features are planned.

## Start your repository

Copy or extract this folder to your chosen project location, then run:

```sh
git init
git add .
git commit -m "Add library backend boilerplate"
```

Create an empty remote repository yourself, then follow its instructions to add the remote and push. No repository or remote has been created by this scaffold.

Reference: [Flask application factories](https://flask.palletsprojects.com/en/stable/patterns/appfactories/).
