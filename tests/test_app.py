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
        self.assertIn(b'action="/#catalog"', home.data)
        self.assertNotIn(b"Design preview", home.data)
        self.assertNotIn(b"Catalog management", home.data)
        self.assertEqual(self.client.get(f"/works/{self.media_id}").status_code, 200)
        self.assertIn(f'next=/works/{self.media_id}'.encode(), self.client.get(f"/works/{self.media_id}").data)
        self.assertEqual(self.client.get("/member").status_code, 302)
        self.assertEqual(self.client.get("/librarian").status_code, 302)
        self.assertEqual(self.client.get("/api/media").status_code, 200)
        self.assertEqual(self.client.get("/api/borrowings").status_code, 401)
        health_data = self.client.get("/api/health").json
        self.assertEqual(health_data["status"], "ok")
        self.assertEqual(health_data["database"], "connected")

    def test_member_borrow_return_and_reading(self):
        response = self.register()
        self.assertIn(b"Your stories, in one place", response.data)
        self.assertEqual(self.client.get("/librarian").status_code, 403)
        for path in ("/librarian/books", "/librarian/members", "/librarian/loans", "/librarian/copies"):
            self.assertEqual(self.client.get(path).status_code, 403)
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
        saved = self.client.post(f"/works/{self.media_id}/progress", data={
            "csrf_token": token, "position": "40",
        })
        self.assertEqual(saved.location, f"/works/{self.media_id}#reader-tools")
        self.client.post(f"/works/{self.media_id}/progress", data={
            "csrf_token": token, "position": "101",
        })
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT current_position FROM reading_progress").fetchone()[0], 40)
        self.assertEqual(self.client.post(f"/works/{self.media_id}/bookmarks", data={
            "csrf_token": token,
        }).status_code, 302)
        self.assertIn(b"40%", self.client.get("/member").data)
        self.assertIn(b"Position 40", self.client.get("/member").data)
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
        self.assertNotIn(b"Account type", self.client.get("/login").data)
        self.assertEqual(self.client.post("/login", data={"username": "staff", "password": "staff-password"}).status_code, 400)
        response = self.client.post("/login", data={
            "csrf_token": self.csrf(), "username": "staff", "password": "staff-password",
        }, follow_redirects=True)
        self.assertIn(b"Hello, ", response.data)
        self.assertIn(b"Physical copies", response.data)
        self.assertIn(b"Members list", response.data)
        self.assertIn(b"A Library Story", response.data)
        self.assertIn(b'href="/librarian/loans"', response.data)
        self.assertIn(b'href="/librarian/copies"', response.data)
        for path in ("/librarian/books", "/librarian/members", "/librarian/loans", "/librarian/copies"):
            self.assertEqual(self.client.get(path).status_code, 200)
        self.assertEqual(self.client.get("/member").status_code, 403)
        self.assertEqual(self.client.get("/").location, "/librarian")
        self.assertNotIn(b"Browse</a>", self.client.get("/librarian").data)
        self.assertIn(b"Settings", self.client.get("/settings").data)
        token = self.csrf()
        response = self.client.post("/librarian/titles/new", data={
            "csrf_token": token, "title": "Second Story", "author": "B. Writer",
            "category": "Novels", "volume": "", "progress_unit": "page",
            "total_units": "120", "description": "Another book.",
        })
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            media_id = get_db().execute("SELECT media_id FROM media_item WHERE title = 'Second Story'").fetchone()[0]
        self.assertIn(b'name="quantity"', self.client.get(f"/librarian/titles/{media_id}/copies/new").data)
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT COUNT(*) FROM media_copy WHERE media_id = ?", (media_id,)).fetchone()[0], 1)
        self.assertEqual(self.client.post(f"/librarian/titles/{media_id}/copies/new", data={
            "csrf_token": token, "quantity": "100",
        }).status_code, 302)
        with self.app.app_context():
            rows = get_db().execute("SELECT accession_number FROM media_copy WHERE media_id = ?", (media_id,)).fetchall()
            self.assertEqual(len(rows), 101)
            self.assertEqual(len({row[0] for row in rows}), 101)
        self.assertIn(b"Second Story", self.client.get("/librarian").data)
        self.assertEqual(self.client.get(f"/librarian/titles/{media_id}/edit").status_code, 200)

    def test_sign_in_returns_member_to_chosen_title(self):
        self.register()
        token = self.csrf()
        self.client.post("/logout", data={"csrf_token": token})
        response = self.client.post("/login", data={
            "csrf_token": self.csrf(), "username": "reader", "password": "reader-password",
            "next": f"/works/{self.media_id}",
        })
        self.assertEqual(response.location, f"/works/{self.media_id}")

    def test_notifications_for_member_and_staff(self):
        self.register()
        token = self.csrf()
        self.client.post(f"/works/{self.media_id}/borrow", data={"csrf_token": token})
        self.assertEqual(self.client.get("/notifications").status_code, 404)
        page = self.client.get("/member")
        self.assertIn(b"You borrowed A Library Story.", page.data)
        self.assertIn(b"1 unread", page.data)
        staff = self.app.test_client()
        staff.post("/login", data={
            "csrf_token": self.csrf(staff), "username": "staff", "password": "staff-password",
        })
        self.assertIn(b"Test Reader borrowed A Library Story.", staff.get("/librarian").data)
        with self.app.app_context():
            member_notice = get_db().execute(
                "SELECT notification_id FROM notification WHERE recipient_role = 'member'"
            ).fetchone()[0]
        self.assertEqual(staff.post(
            f"/notifications/{member_notice}/read",
            data={"csrf_token": self.csrf(staff)},
        ).status_code, 404)
        self.client.post("/notifications/read", data={"csrf_token": token})
        self.assertNotIn(b"Mark all read", self.client.get("/member").data)
        self.assertIn(b"Clear all", self.client.get("/member").data)
        self.assertIn(b'notification-dropdown-item ', self.client.get("/member").data)
        self.assertIn(b"1 unread", staff.get("/librarian").data)
        with self.app.app_context():
            borrowing_id = get_db().execute("SELECT borrowing_id FROM borrowing_record").fetchone()[0]
        self.client.post(
            f"/member/borrowings/{borrowing_id}/return",
            data={"csrf_token": token},
        )
        self.assertIn(b"You returned A Library Story.", self.client.get("/member").data)
        self.assertIn(b"Test Reader returned A Library Story.", staff.get("/librarian").data)
        self.assertEqual(self.client.post("/notifications/clear", data={"csrf_token": token}).status_code, 302)
        self.assertIn(b"No notifications yet", self.client.get("/member").data)
        self.assertIn(b"Test Reader returned A Library Story.", staff.get("/librarian").data)

    def test_api_member_workflow(self):
        token = self.client.get("/api/session").json["csrf_token"]
        created = self.client.post("/api/members", json={
            "full_name": "API Reader", "username": "api-reader", "password": "reader-password",
        }, headers={"X-CSRF-Token": token})
        self.assertEqual(created.status_code, 201)
        login = self.client.post("/api/session", json={
            "username": "api-reader", "password": "reader-password",
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

    def test_genres_and_circulation_analytics_sheets(self):
        # 1. Staff logs in
        staff = self.app.test_client()
        staff.post("/login", data={
            "csrf_token": self.csrf(staff), "username": "staff", "password": "staff-password",
        })

        # 2. Add media with genres or auto-draft
        token = self.csrf(staff)
        res = staff.post("/librarian/titles/new", data={
            "csrf_token": token, "title": "Cyberpunk Chronicles", "author": "K. Neo",
            "category": "Manga", "progress_unit": "chapter", "total_units": "50",
            "description": "A dark cyberpunk sci-fi thriller about hackers and neon alleyways.",
        })
        self.assertEqual(res.status_code, 302)

        with self.app.app_context():
            from app.services.media import get_media_genres
            m_id = get_db().execute("SELECT media_id FROM media_item WHERE title = 'Cyberpunk Chronicles'").fetchone()[0]
            genres = get_media_genres(m_id)
            self.assertTrue(len(genres) > 0)
            self.assertTrue(any(g in ("Manga", "Sci-Fi", "Cyberpunk", "Thriller", "Action") for g in genres))

            # Add copy and borrow
            copy_res = staff.post(f"/librarian/titles/{m_id}/copies/new", data={
                "csrf_token": token, "quantity": "2",
            })
            self.assertEqual(copy_res.status_code, 302)
            c_id = get_db().execute("SELECT copy_id FROM media_copy WHERE media_id = ?", (m_id,)).fetchone()[0]

        # 3. Member borrows this cyberpunk manga
        self.register("manga-fan")
        mem_token = self.csrf()
        borrow_res = self.client.post("/api/borrowings", json={"copy_id": c_id}, headers={"X-CSRF-Token": mem_token})
        self.assertEqual(borrow_res.status_code, 201)

        # 4. Staff checks dashboard sheets
        dash = staff.get("/librarian")
        self.assertEqual(dash.status_code, 200)
        self.assertIn(b"Circulation &amp; Popularity Sheets", dash.data)
        self.assertIn(b"Top Genres Borrowed", dash.data)
        self.assertIn(b"Top Book Types", dash.data)
        self.assertIn(b"Book Borrowing Rankings", dash.data)
        self.assertIn(b"Cyberpunk Chronicles", dash.data)

        # 5. Staff checks dedicated /librarian/analytics page
        analytics_page = staff.get("/librarian/analytics")
        self.assertEqual(analytics_page.status_code, 200)
        self.assertIn(b"Staff Analytics <em>Sheets</em>", analytics_page.data)
        self.assertIn(b"Top Genres Borrowed", analytics_page.data)
        self.assertIn(b"Top Book Types &amp; Categories Borrowed", analytics_page.data)
        self.assertIn(b"Book Borrowing Leaderboard Rankings", analytics_page.data)
        self.assertIn(b"Cyberpunk Chronicles", analytics_page.data)

        # Member should be denied access to /librarian/analytics
        self.assertEqual(self.client.get("/librarian/analytics").status_code, 403)

        # 6. Check REST analytics endpoints
        staff_api_token = staff.get("/api/session").json["csrf_token"]
        top_genres = staff.get("/api/analytics/top-genres", headers={"X-CSRF-Token": staff_api_token})
        self.assertEqual(top_genres.status_code, 200)
        self.assertIsInstance(top_genres.json, list)
        self.assertTrue(len(top_genres.json) > 0)

        top_types = staff.get("/api/analytics/top-book-types", headers={"X-CSRF-Token": staff_api_token})
        self.assertEqual(top_types.status_code, 200)
        self.assertIsInstance(top_types.json, list)

        book_rankings = staff.get("/api/analytics/book-rankings", headers={"X-CSRF-Token": staff_api_token})
        self.assertEqual(book_rankings.status_code, 200)
        self.assertIsInstance(book_rankings.json, list)
        self.assertEqual(book_rankings.json[0]["title"], "Cyberpunk Chronicles")
        self.assertEqual(book_rankings.json[0]["borrow_count"], 1)

    def test_librarian_open_library_with_provider_dropdown_toggle(self):
        staff = self.librarian_client()
        # 1. Access page and verify dropdown toggle elements
        res = staff.get("/librarian/open-library")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'id="provider"', res.data)
        self.assertIn(b"Open Library (Primary API)", res.data)
        self.assertIn(b"Google Books (Secondary API)", res.data)

        # 2. Search using Google Books secondary provider
        mock_results = [
            {
                "source_key": "/googlebooks/testvol123",
                "title": "Chainsaw Demon",
                "author": "Tatsuki Fujimoto",
                "cover": "catalog-placeholder.svg",
                "total_units": 190,
                "category": "Manga",
                "genres": ["Manga", "Action", "Supernatural"],
                "first_publish_year": 2018,
                "provider": "googlebooks",
                "import_token": "mocked-token-for-test"
            }
        ]
        with unittest.mock.patch("app.services.google_books.search_google_books", return_value=mock_results):
            gb_res = staff.get("/librarian/open-library?q=Chainsaw&provider=googlebooks")
            self.assertEqual(gb_res.status_code, 200)
            self.assertIn(b"Chainsaw Demon", gb_res.data)
            self.assertIn(b"Google Books", gb_res.data)
            self.assertIn(b"Supernatural", gb_res.data)


if __name__ == "__main__":
    unittest.main()

