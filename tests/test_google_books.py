import io
import json
import unittest
from unittest.mock import patch

from app import create_app
from app.services.google_books import (
    _clean_category_name,
    draft_genre_tags_for_book,
    fetch_genres_from_google_books,
    fetch_genres_from_open_library,
    search_google_books,
)


class ExternalBooksApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-key-for-tokens"})
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_clean_category_name(self):
        raw = "Comics & Graphic Novels / Manga / Action & Adventure"
        tags = _clean_category_name(raw)
        self.assertIn("Manga", tags)
        self.assertIn("Action", tags)

    def test_fetch_genres_from_open_library_primary_with_subjects(self):
        subjects = ["Fantasy fiction", "Superheroes", "Comics", "Graphic novels"]
        genres = fetch_genres_from_open_library("Batman", subjects=subjects)
        self.assertIn("Fantasy", genres)
        self.assertIn("Superheroes", genres)

    def test_fetch_genres_from_google_books_secondary_with_mocked_api(self):
        mock_response = {
            "items": [
                {
                    "volumeInfo": {
                        "title": "Naruto, Vol. 1",
                        "authors": ["Masashi Kishimoto"],
                        "categories": [
                            "Juvenile Fiction / Comics & Graphic Novels / Manga / Action & Adventure"
                        ],
                        "description": "Naruto is a ninja-in-training with a need for recognition.",
                    }
                }
            ]
        }
        bytes_stream = io.BytesIO(json.dumps(mock_response).encode("utf-8"))
        with patch("app.services.google_books.urlopen", return_value=bytes_stream):
            genres = fetch_genres_from_google_books("Naruto", "Masashi Kishimoto")
            self.assertIn("Manga", genres)
            self.assertIn("Action", genres)

    def test_search_google_books_secondary_api(self):
        mock_response = {
            "items": [
                {
                    "id": "abc123volume",
                    "volumeInfo": {
                        "title": "Attack on Titan Vol. 1",
                        "authors": ["Hajime Isayama"],
                        "publishedDate": "2012-06-19",
                        "pageCount": 192,
                        "categories": ["Comics & Graphic Novels / Manga"],
                        "imageLinks": {
                            "thumbnail": "http://books.google.com/thumbnail.jpg"
                        },
                        "description": "Humans live inside cities surrounded by enormous walls.",
                    }
                }
            ]
        }
        bytes_stream = io.BytesIO(json.dumps(mock_response).encode("utf-8"))
        with patch("app.services.google_books.urlopen", return_value=bytes_stream):
            results = search_google_books("Attack on Titan")
            self.assertEqual(len(results), 1)
            book = results[0]
            self.assertEqual(book["source_key"], "/googlebooks/abc123volume")
            self.assertEqual(book["title"], "Attack on Titan Vol. 1")
            self.assertEqual(book["category"], "Manga")
            self.assertEqual(book["provider"], "googlebooks")
            self.assertTrue(book["cover"].startswith("https://"))
            self.assertIsNotNone(book["import_token"])

    def test_draft_genre_tags_provider_toggle(self):
        # Toggling provider=googlebooks vs provider=openlibrary
        tags_ol = draft_genre_tags_for_book(
            title="Dune",
            author="Frank Herbert",
            category="Novels",
            description="Epic sci-fi desert planet story with space politics.",
            provider="openlibrary"
        )
        self.assertIn("Sci-Fi", tags_ol)

        tags_gb = draft_genre_tags_for_book(
            title="Dune",
            author="Frank Herbert",
            category="Novels",
            description="Epic sci-fi desert planet story with space politics.",
            provider="googlebooks"
        )
        self.assertIn("Sci-Fi", tags_gb)

    def test_draft_genre_tags_fallback_on_network_error(self):
        with patch("app.services.google_books.urlopen", side_effect=TimeoutError("Network down")):
            tags = draft_genre_tags_for_book(
                title="Ghost in the Shell",
                author="Masamune Shirow",
                category="Manga",
                description="Cyberpunk investigation into an elusive hacker called the Puppet Master.",
                provider="openlibrary"
            )
            self.assertTrue(len(tags) > 0)
            self.assertIn("Manga", tags)
            self.assertTrue(any(t in ("Cyberpunk", "Sci-Fi", "Action") for t in tags))

    def test_draft_genre_tags_non_empty(self):
        tags = draft_genre_tags_for_book(
            title="Random Obscure Book",
            author="Unknown",
            category="Novels",
            description="",
        )
        self.assertIsInstance(tags, list)
        self.assertTrue(len(tags) >= 1)
