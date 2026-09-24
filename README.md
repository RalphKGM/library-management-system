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

The member and catalog features currently run through Python service functions. They do not have API routes yet. Borrowing, returns, reading progress and bookmarks are still being built

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

Open http://127.0.0.1:5000/api/health in your browser. You should see `{"status":"ok"}`

There is no homepage yet so opening http://127.0.0.1:5000/ will show a 404. Press Ctrl+C in the terminal to stop the server. When you run it again later you only need to activate the virtual environment and run the last command

## Project files

```text
app/
  __init__.py       Flask app setup
  db.py             SQLite connection and database setup
  schema.sql        Database tables
  routes.py         Health endpoint
  models.py         Record classes
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
3. Add API routes, login sessions, validation and tests

Borrowing has no fee. There are no payment features in this project
