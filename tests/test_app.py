import tempfile
import unittest
from pathlib import Path

from app import create_app
from app.db import get_db, init_db
from app.services.media import add_copy, add_media
from app.services.members import create_librarian


class LibraryWebsiteTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "DATABASE": str(Path(self.folder.name) / "library.sqlite3")})
        with self.app.app_context():
            init_db()
            staff = create_librarian("staff", "staff-password")
            work = add_media({
                "title": "A Library Story", "author": "A. Writer", "category": "Manga",
                "total_units": 100, "description": "A story about a library.",
            }, staff["librarian_id"])
            copy = add_copy(work["media_id"], "COPY-001", staff["librarian_id"])
            self.media_id = work["media_id"]
            self.copy_id = copy["copy_id"]
        self.client = self.app.test_client()

    def tearDown(self):
        self.folder.cleanup()

    def csrf(self, client=None):
        client = client or self.client
        client.get("/login")
        with client.session_transaction() as session:
            return session["csrf_token"]

    def register(self, username="reader", client=None):
        client = client or self.client
        return client.post("/register", data={
            "csrf_token": self.csrf(client), "name": "Test Reader",
            "username": username, "password": "reader-password",
        }, follow_redirects=True)

    def test_public_catalog_and_role_boundaries(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn(b"A Library Story", home.data)
        self.assertNotIn(b"Design preview", home.data)
        self.assertNotIn(b"Catalog management", home.data)
        self.assertEqual(self.client.get(f"/works/{self.media_id}").status_code, 200)
        self.assertEqual(self.client.get("/member").status_code, 302)
        self.assertEqual(self.client.get("/librarian").status_code, 302)
        self.assertEqual(self.client.get("/api/media").status_code, 200)
        self.assertEqual(self.client.get("/api/borrowings").status_code, 401)
        self.assertEqual(self.client.get("/api/health").json, {"status": "ok"})

    def test_member_borrow_return_and_reading(self):
        response = self.register()
        self.assertIn(b"Your stories, in one place", response.data)
        self.assertEqual(self.client.get("/librarian").status_code, 403)
        self.assertIn(b"My Library", self.client.get("/").data)
        self.assertNotIn(b"Catalog management", self.client.get("/").data)
        token = self.csrf()
        self.assertEqual(self.client.post(f"/works/{self.media_id}/borrow", data={"csrf_token": token}).status_code, 302)
        self.assertIn(b"A Library Story", self.client.get("/member").data)
        self.assertIn(b"0 available of 1", self.client.get(f"/works/{self.media_id}").data)
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT COUNT(*) FROM borrowing_record WHERE returned_at IS NULL").fetchone()[0], 1)
        self.assertIn(b"already have this title borrowed", self.client.post(
            "/api/borrowings", json={"copy_id": self.copy_id}, headers={"X-CSRF-Token": token}
        ).data)
        self.assertEqual(self.client.post(f"/works/{self.media_id}/progress", data={
            "csrf_token": token, "position": "40", "status": "reading",
        }).status_code, 302)
        self.client.post(f"/works/{self.media_id}/progress", data={
            "csrf_token": token, "position": "101", "status": "reading",
        })
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT current_position FROM reading_progress").fetchone()[0], 40)
        self.assertEqual(self.client.post(f"/works/{self.media_id}/bookmarks", data={
            "csrf_token": token, "position": "25", "note": "Good chapter",
        }).status_code, 302)
        self.assertIn(b"40%", self.client.get("/member").data)
        self.assertIn(b"Good chapter", self.client.get("/member").data)
        with self.app.app_context():
            borrowing_id = get_db().execute("SELECT borrowing_id FROM borrowing_record").fetchone()[0]
            bookmark_id = get_db().execute("SELECT bookmark_id FROM bookmark").fetchone()[0]
        other = self.app.test_client()
        self.register("other-reader", other)
        self.assertEqual(other.post(f"/member/borrowings/{borrowing_id}/return", data={"csrf_token": self.csrf(other)}).status_code, 404)
        self.assertEqual(other.post(f"/bookmarks/{bookmark_id}/delete", data={"csrf_token": self.csrf(other)}).status_code, 404)
        self.assertEqual(self.client.post(f"/member/borrowings/{borrowing_id}/return", data={"csrf_token": token}).status_code, 302)
        self.assertEqual(self.client.post(f"/member/borrowings/{borrowing_id}/return", data={"csrf_token": token}).status_code, 404)
        self.assertEqual(self.client.post(f"/bookmarks/{bookmark_id}/delete", data={"csrf_token": token}).status_code, 302)
        self.assertIn(b"A Library Story", self.client.get("/member").data)

    def test_librarian_forms_and_csrf(self):
        self.assertEqual(self.client.post("/login", data={"username": "staff", "password": "staff-password", "role": "librarian"}).status_code, 400)
        response = self.client.post("/login", data={
            "csrf_token": self.csrf(), "username": "staff", "password": "staff-password", "role": "librarian",
        }, follow_redirects=True)
        self.assertIn(b"Catalog management", response.data)
        self.assertEqual(self.client.get("/member").status_code, 403)
        self.assertNotIn(b"My Library", self.client.get("/").data)
        token = self.csrf()
        response = self.client.post("/librarian/titles/new", data={
            "csrf_token": token, "title": "Second Story", "author": "B. Writer",
            "category": "Novels", "volume": "", "progress_unit": "page",
            "total_units": "120", "description": "Another book.",
        })
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            media_id = get_db().execute("SELECT media_id FROM media_item WHERE title = 'Second Story'").fetchone()[0]
        self.assertEqual(self.client.post(f"/librarian/titles/{media_id}/copies/new", data={
            "csrf_token": token, "accession": "COPY-002",
        }).status_code, 302)
        self.assertIn(b"Second Story", self.client.get("/").data)
        self.assertEqual(self.client.get(f"/librarian/titles/{media_id}/edit").status_code, 200)

    def test_api_member_workflow(self):
        token = self.client.get("/api/session").json["csrf_token"]
        created = self.client.post("/api/members", json={
            "full_name": "API Reader", "username": "api-reader", "password": "reader-password",
        }, headers={"X-CSRF-Token": token})
        self.assertEqual(created.status_code, 201)
        login = self.client.post("/api/session", json={
            "role": "member", "username": "api-reader", "password": "reader-password",
        }, headers={"X-CSRF-Token": token})
        self.assertEqual(login.status_code, 200)
        token = login.json["csrf_token"]
        borrowing = self.client.post("/api/borrowings", json={"copy_id": self.copy_id}, headers={"X-CSRF-Token": token})
        self.assertEqual(borrowing.status_code, 201)
        progress = self.client.put(f"/api/media/{self.media_id}/progress", json={
            "position": 20, "status": "reading",
        }, headers={"X-CSRF-Token": token})
        self.assertEqual(progress.status_code, 200)
        self.assertEqual(self.client.get(f"/api/media/{self.media_id}/progress").json["current_position"], 20)
        self.assertEqual(self.client.post(f"/api/borrowings/{borrowing.json['borrowing_id']}/return", headers={"X-CSRF-Token": token}).status_code, 200)


if __name__ == "__main__":
    unittest.main()
