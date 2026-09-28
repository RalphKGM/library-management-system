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
python -m flask --app app run --debug
```

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m flask --app app init-db
python -m flask --app app run --debug
```

Open http://127.0.0.1:5000/. The catalog starts empty. Librarians can search Open Library to import title details and covers or add a title manually. The app suggests a category from Open Library subjects. Edit the title if that category needs correcting. The website adds the first physical copy automatically. To add more, enter a quantity and the app generates unique copy IDs.

To create a librarian account, run `python -m flask --app app create-librarian` and enter a username and password when prompted. Member accounts are created through the website. The librarian command does not create a public registration route for staff.

## What each role can use

| Role | Pages and actions |
| --- | --- |
| Guest | Browse and search the catalog, view title details, register, sign in |
| Member | Guest pages plus My Library, borrowing, returns, reading progress, and bookmarks |
| Librarian | Dashboard, Books, Members, Loans, Physical Copies, Open Library import, and title editing |

Staff are sent to the dashboard when they open the home page. Members and guests use Browse. Signed-in users can open Settings to switch color themes. Notifications disappear after seven seconds or can be closed sooner. Navigation shows the pages for the signed-in role. The server also checks permissions on every protected page and action.
The sign-in form uses a single username and password flow and identifies the account type automatically. Members who sign in from a title page return to that title. Catalog filters keep the results section in view, while reading bookmarks use the member's saved page or chapter. Staff can add up to 500 physical copies at once without entering IDs.

## API

The JSON API includes catalog browsing, member registration and sessions, borrowing and returns, reading progress, bookmarks, librarian catalog actions, and librarian-only Open Library search and import. `GET /api/health` returns `{"status":"ok"}`.

Open Library routes are `GET /api/open-library/search?q=...` and `POST /api/open-library/import` with an `import_token` from a search result. The category is included in that result. Search results expire after 30 minutes.

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

## Run with Docker instead

Start Docker Desktop first. From the project folder run `docker compose up -d --build` then open http://127.0.0.1:5001/. The SQLite database stays in the local `instance/` folder. To create a librarian account run `docker compose exec web python -m flask --app app create-librarian`. Use `docker compose down` to stop the container. Stop any local Flask server on port 5001 before starting Docker.

Docker is optional. SQLite works directly with Flask and does not need a database container. When you run Flask in Terminal, that terminal stays busy showing server logs until you press Ctrl+C. Open another Terminal tab for other commands or run Docker in the background with `-d`.
