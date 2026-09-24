# Entertainment Media Library Management System

Group 2 | Principles of Programming Languages

A library system for manga, comics, novels, magazines and graphic novels

Members can register and log in. Librarians can manage titles and physical copies. The project uses Flask and SQLite

## What works now

- Create the database with the `init-db` command
- Register and authenticate members with hashed passwords
- Create and authenticate librarian accounts
- Add, update and search media titles
- Add physical copies and check which copies are available
- Check that the server is running at `/api/health`
- Browse the collection through the new responsive website at `/`
- View title details, member area, sign-in and registration layouts, and the librarian workspace

The browse page reads real titles and copy availability from SQLite. While the database has no titles, it displays clearly labeled sample works to preview the design. Member and catalog service functions do not have API routes yet. Website forms are visual previews, and borrowing, returns, reading progress and bookmarks are still being built

## How to run

You need Python 3.9 or newer

### macOS or Linux

Open a terminal in this project folder and run

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

Open http://127.0.0.1:5000/ in your browser to see the website. The health endpoint remains at http://127.0.0.1:5000/api/health

Press Ctrl+C in the terminal to stop the server. When you run it again later you only need to activate the virtual environment and run the last command

## Project files

```text
app/
  __init__.py       Flask app setup
  db.py             SQLite connection and database setup
  schema.sql        Database tables
  routes.py         Health endpoint
  models.py         Record classes
  ui.py             Website pages and database catalog display
  demo_catalog.py   Clearly labeled sample works for an empty database
  templates/        Website layouts and page templates
  static/           Styles, JavaScript and sample cover art
  services/
    members.py      Members and librarians
    media.py        Titles and copies
    borrowing.py    Borrowing and returns to build
    reading.py      Progress and bookmarks to build
    helpers.py      Helper functions to build
tests/
  README.md         Test ideas
requirements.txt   Python packages
```

## Next steps

1. Build borrowing and returns
2. Build reading progress and bookmarks
3. Connect website forms, API routes, login sessions, validation and tests

Borrowing has no fee. There are no payment features in this project
