# Tests

Run the application tests from the project root:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

The tests exercise registration and sign in, role restricted pages and API routes, CSRF protection, catalog management, borrowing and returns, reading progress, bookmarks, and member ownership checks. Each test uses a temporary SQLite database.
