import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.services.media import add_media


WORK_KEY = re.compile(r"^/works/OL[0-9]+W$")
SEARCH_URL = "https://openlibrary.org/search.json"


def _signer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="open-library-import")


def search_books(query):
    if not isinstance(query, str) or not query.strip():
        raise ValueError("enter a title or author to search")
    query = query.strip()
    if len(query) > 120:
        raise ValueError("search must be at most 120 characters")
    params = urlencode({"q": query, "fields": "key,title,author_name,cover_i,first_publish_year,number_of_pages_median", "limit": 10})
    request = Request(f"{SEARCH_URL}?{params}", headers={"User-Agent": "TheReadingRoom/1.0 (educational library project)"})
    try:
        with urlopen(request, timeout=6) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise ConnectionError("Open Library is unavailable. Try again later or add the title manually.") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("docs"), list):
        raise ConnectionError("Open Library returned an unexpected response.")
    results = []
    for doc in payload["docs"]:
        if not isinstance(doc, dict):
            continue
        key = doc.get("key")
        title = doc.get("title")
        if not isinstance(key, str) or not WORK_KEY.fullmatch(key) or not isinstance(title, str) or not title.strip():
            continue
        authors = doc.get("author_name")
        author = ", ".join(name for name in authors[:3] if isinstance(name, str)) if isinstance(authors, list) else ""
        cover_id = doc.get("cover_i")
        cover = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if type(cover_id) is int and cover_id > 0 else "catalog-placeholder.svg"
        pages = doc.get("number_of_pages_median")
        data = {
            "source_key": key,
            "title": title.strip()[:300],
            "author": author[:300] or "Unknown author",
            "cover": cover,
            "total_units": pages if type(pages) is int and 0 < pages <= 100000 else None,
        }
        results.append({**data, "first_publish_year": doc.get("first_publish_year"), "import_token": _signer().dumps(data)})
    return results


def import_book(token, category, librarian_id):
    try:
        data = _signer().loads(token, max_age=1800)
    except (BadSignature, SignatureExpired, TypeError) as exc:
        raise ValueError("search result expired. Search again.") from exc
    if not isinstance(data, dict) or not WORK_KEY.fullmatch(str(data.get("source_key", ""))):
        raise ValueError("invalid Open Library result")
    from app.sample_catalog import CATEGORIES

    if category not in CATEGORIES:
        raise ValueError("choose a valid category")
    details = {name: data.get(name) for name in ("title", "author", "cover", "total_units")}
    details["category"] = category
    details["source_key"] = data["source_key"]
    return add_media(details, librarian_id)
