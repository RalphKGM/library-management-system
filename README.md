# Entertainment Media Library Management System

Group 2 | Principles of Programming Languages

A Flask and SQLite library for manga, comics, literature, novels, magazines, and graphic novels. Registered members can borrow available physical copies for free. Librarians manage titles and copies. There are no fees or payment features.

## Run locally

Use Python 3.9 or newer.

### macOS or Linux

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m flask --app app init-db
python -m flask --app app seed-sample
python -m flask --app app run --debug
```

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m flask --app app init-db
python -m flask --app app seed-sample
python -m flask --app app run --debug
```

Open http://127.0.0.1:5000/. The `seed-sample` step is optional and only works when the catalog is empty. It adds fictional starter titles and physical copies so the browse pages can be explored. You can leave it out and add your own titles as a librarian.

To create a librarian account, run `python -m flask --app app create-librarian` and enter a username and password when prompted. Member accounts are created through the website. The librarian command does not create a public registration route for staff.

## What each role can use

| Role | Pages and actions |
| --- | --- |
| Guest | Browse and search the catalog, view title details, register, sign in |
| Member | Guest pages plus My Library, borrowing, returns, reading progress, and bookmarks |
| Librarian | Guest pages plus catalog management, title editing, and copy creation |

Navigation shows the pages for the signed-in role. The server also checks permissions on every protected page and action. Member and librarian accounts use separate sign-in options.

## API

The JSON API includes catalog browsing, member registration and sessions, borrowing and returns, reading progress, bookmarks, and librarian catalog actions. `GET /api/health` returns `{"status":"ok"}`.

For API writes, first call `GET /api/session`. Send its `csrf_token` in the `X-CSRF-Token` header. Sign-in returns a new token for later writes. The API uses the same session cookie as the website.

## Tests

```sh
python -m unittest discover -s tests -v
```

Tests cover public browsing, role restrictions, form token checks, librarian edits, member borrowing and returns, reading activity, and API access.

## Project files

```text
app/
  __init__.py       Flask setup and session secret
  db.py             SQLite setup and CLI commands
  schema.sql        Database tables and active-copy constraint
  security.py       Session identity, role checks, and form tokens
  routes.py         JSON API
  ui.py             Website pages and form actions
  sample_catalog.py Optional starter titles
  services/         Member, media, borrowing, and reading operations
  templates/        Website pages
  static/           CSS, JavaScript, and cover illustrations
tests/
  test_app.py       Workflow and role tests
```
