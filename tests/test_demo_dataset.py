import tempfile
import unittest
from pathlib import Path

from app import create_app
from app.db import get_db
from app.services.members import authenticate_member, create_librarian


class DemoDatasetTests(unittest.TestCase):
    def test_seed_is_sourced_and_repeatable(self):
        with tempfile.TemporaryDirectory() as folder:
            app = create_app({
                "TESTING": True,
                "DATABASE": str(Path(folder) / "demo.sqlite3"),
            })
            with app.app_context():
                create_librarian("staff", "staff-password")
            runner = app.test_cli_runner()
            first = runner.invoke(args=["seed-demo"])
            self.assertEqual(first.exit_code, 0, first.output)
            with app.app_context():
                db = get_db()
                counts = db.execute(
                    "SELECT category, COUNT(*) AS titles FROM media_item GROUP BY category"
                ).fetchall()
                self.assertEqual(len(counts), 6)
                self.assertTrue(all(row["titles"] == 10 for row in counts))
                self.assertEqual(db.execute("SELECT COUNT(*) FROM member").fetchone()[0], 10)
                self.assertEqual(db.execute(
                    "SELECT COUNT(*) FROM media_item WHERE source_key LIKE '/works/OL%W'"
                ).fetchone()[0], 60)
                stock = {
                    row[0] for row in db.execute(
                        "SELECT COUNT(c.copy_id) FROM media_item m "
                        "LEFT JOIN media_copy c ON c.media_id = m.media_id GROUP BY m.media_id"
                    )
                }
                self.assertGreaterEqual(len(stock), 5)
                self.assertIsNotNone(authenticate_member("demo_reader_01", "DemoReader2026!"))
            second = runner.invoke(args=["seed-demo"])
            self.assertEqual(second.exit_code, 0, second.output)
            self.assertIn("Added 0 Open Library books", second.output)
