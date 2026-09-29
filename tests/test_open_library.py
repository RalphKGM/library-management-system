import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.db import get_db, init_db
from app.services.members import create_librarian


class OpenLibraryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "DATABASE": str(Path(self.folder.name) / "library.sqlite3")})
        with self.app.app_context():
            init_db()
            create_librarian("staff", "staff-password")
        self.client = self.app.test_client()

    def tearDown(self):
        self.folder.cleanup()

    def login(self):
        token = self.client.get("/api/session").json["csrf_token"]
        result = self.client.post("/api/session", json={"username": "staff", "password": "staff-password"}, headers={"X-CSRF-Token": token})
        return result.json["csrf_token"]

    def test_search_and_import_requires_librarian_and_creates_no_copy(self):
        self.assertEqual(self.client.get("/api/open-library/search?q=story").status_code, 401)
        token = self.login()
        payload = {"docs": [{"key": "/works/OL123W", "title": "The Story", "author_name": ["A. Writer"], "cover_i": 456, "number_of_pages_median": 90, "subject": ["Fiction", "Fantasy"]}, {"key": "bad", "title": "Skip"}]}
        response = io.BytesIO(json.dumps(payload).encode())
        with patch("app.services.open_library.urlopen", return_value=response):
            search = self.client.get("/api/open-library/search?q=story")
        self.assertEqual(search.status_code, 200)
        self.assertEqual(len(search.json), 1)
        with patch("app.services.open_library.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
            page = self.client.get("/librarian/open-library?q=story")
            self.assertIn(b"The Story", page.data)
            self.assertIn(b"book-search-results-list", page.data)
        self.assertEqual(search.json[0]["cover"], "https://covers.openlibrary.org/b/id/456-M.jpg")
        self.assertEqual(search.json[0]["category"], "Novels")
        data = {"import_token": search.json[0]["import_token"]}
        imported = self.client.post("/api/open-library/import", json=data, headers={"X-CSRF-Token": token})
        self.assertEqual(imported.status_code, 201)
        self.assertEqual(imported.json["source_key"], "/works/OL123W")
        self.assertEqual(imported.json["category"], "Novels")
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT COUNT(*) FROM media_copy").fetchone()[0], 0)
        self.assertIn(b"456-M.jpg", self.client.get("/librarian").data)
        self.assertIn(b"openlibrary.org/works/OL123W", self.app.test_client().get(f"/works/{imported.json['media_id']}").data)
        self.assertEqual(self.client.post("/api/open-library/import", json=data, headers={"X-CSRF-Token": token}).status_code, 400)

    def test_invalid_import_and_upstream_failure(self):
        token = self.login()
        self.assertEqual(self.client.post("/api/open-library/import", json={"import_token": "bad", "category": "Manga"}, headers={"X-CSRF-Token": token}).status_code, 400)
        with patch("app.services.open_library.urlopen", side_effect=TimeoutError):
            self.assertEqual(self.client.get("/api/open-library/search?q=story").status_code, 503)


if __name__ == "__main__":
    unittest.main()
