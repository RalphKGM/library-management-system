import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"
OPEN_LIBRARY_SEARCH = "https://openlibrary.org/search.json"

# Normalized standard genre labels
CANONICAL_GENRES = [
    "Action", "Adventure", "Fantasy", "Sci-Fi", "Mystery", "Romance", "Horror",
    "Thriller", "Slice of Life", "Drama", "Supernatural", "Comedy", "Historical",
    "Superheroes", "Cyberpunk", "Literary Fiction", "Classic", "Arts & Culture",
    "Design", "Periodical", "Coming of Age", "Shonen", "Seinen", "Urban Fantasy"
]

GENRE_KEYWORD_MAP = {
    "manga": "Manga",
    "shonen": "Shonen",
    "seinen": "Seinen",
    "superhero": "Superheroes",
    "superheroes": "Superheroes",
    "comic": "Comics",
    "comics": "Comics",
    "graphic novel": "Graphic Novel",
    "fantasy": "Fantasy",
    "magic": "Fantasy",
    "sci-fi": "Sci-Fi",
    "science fiction": "Sci-Fi",
    "space": "Sci-Fi",
    "cyberpunk": "Cyberpunk",
    "mystery": "Mystery",
    "detective": "Mystery",
    "crime": "Mystery",
    "romance": "Romance",
    "horror": "Horror",
    "ghost": "Horror",
    "thriller": "Thriller",
    "slice of life": "Slice of Life",
    "everyday": "Slice of Life",
    "school": "Slice of Life",
    "drama": "Drama",
    "supernatural": "Supernatural",
    "spirit": "Supernatural",
    "demon": "Supernatural",
    "comedy": "Comedy",
    "humor": "Comedy",
    "historical": "Historical",
    "history": "Historical",
    "literature": "Literary Fiction",
    "poetry": "Literary Fiction",
    "classic": "Classic",
    "classics": "Classic",
    "periodical": "Periodical",
    "magazine": "Periodical",
    "art": "Arts & Culture",
    "design": "Design",
    "coming of age": "Coming of Age",
    "urban": "Urban Fantasy",
}


def _clean_category_name(raw_name):
    """Normalize a category or subject string into clean canonical genre tags."""
    if not isinstance(raw_name, str):
        return []
    
    text = raw_name
    for noise in ("Juvenile Fiction /", "Young Adult Fiction /", "Fiction /", "Nonfiction /", "/ General"):
        text = text.replace(noise, "")
    
    segments = re.split(r"[/,;&]", text)
    results = []
    for seg in segments:
        s = seg.strip()
        if not s or s.lower() in ("general", "fiction", "nonfiction", "juvenile"):
            continue
        matched = False
        lower_s = s.lower()
        for kw, canonical in GENRE_KEYWORD_MAP.items():
            if kw in lower_s:
                results.append(canonical)
                matched = True
                break
        if not matched and len(s) >= 3 and len(s) <= 24:
            results.append(s.title())
    return results


def fetch_genres_from_open_library(title, author="", subjects=None):
    """
    Primary API: Query Open Library or parse subjects to retrieve canonical genre tags.
    """
    subject_list = []
    if isinstance(subjects, list) and subjects:
        subject_list.extend(subjects)
    elif isinstance(title, str) and title.strip():
        clean_title = re.sub(r"\s+[0-9]+$", "", title.strip())
        query = clean_title
        if author and isinstance(author, str) and author.strip():
            query += f" {author.split(',')[0].strip()}"
        params = urlencode({"q": query, "fields": "subject,title", "limit": 2})
        url = f"{OPEN_LIBRARY_SEARCH}?{params}"
        req = Request(url, headers={"User-Agent": "TheReadingRoom/1.0 (Educational Project)"})
        try:
            with urlopen(req, timeout=5) as response:
                data = json.load(response)
                for doc in data.get("docs", []):
                    subs = doc.get("subject", [])
                    if isinstance(subs, list):
                        subject_list.extend(subs[:15])
        except (HTTPError, URLError, TimeoutError, ValueError, OSError):
            pass

    if not subject_list:
        return []

    mapped_genres = []
    for sub in subject_list:
        if isinstance(sub, str):
            mapped_genres.extend(_clean_category_name(sub))

    seen = set()
    deduped = []
    for g in mapped_genres:
        if g not in seen:
            seen.add(g)
            deduped.append(g)
    return deduped[:4]


def fetch_genres_from_google_books(title, author=""):
    """Secondary API: Query Google Books API to retrieve categories and genre hints."""
    if not isinstance(title, str) or not title.strip():
        return []

    clean_title = re.sub(r"\s+[0-9]+$", "", title.strip())
    query_parts = [f'intitle:"{clean_title}"']
    if author and isinstance(author, str) and author.strip():
        first_author = author.split(",")[0].strip()
        query_parts.append(f'inauthor:"{first_author}"')
    
    query = " ".join(query_parts)
    params = urlencode({"q": query, "maxResults": 3})
    url = f"{GOOGLE_BOOKS_API}?{params}"
    
    req = Request(url, headers={"User-Agent": "TheReadingRoom/1.0 (Educational Project)"})
    
    try:
        with urlopen(req, timeout=5) as response:
            data = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        return []

    if not isinstance(data, dict) or "items" not in data:
        return []

    genres = []
    for item in data.get("items", []):
        volume_info = item.get("volumeInfo", {})
        raw_cats = volume_info.get("categories", [])
        if isinstance(raw_cats, list):
            for cat in raw_cats:
                genres.extend(_clean_category_name(cat))
        
        desc = volume_info.get("description", "")
        if isinstance(desc, str) and len(genres) < 2:
            lower_desc = desc.lower()
            for kw, canonical in GENRE_KEYWORD_MAP.items():
                if kw in lower_desc and canonical not in genres:
                    genres.append(canonical)
                    if len(genres) >= 4:
                        break

    seen = set()
    deduped = []
    for g in genres:
        if g not in seen:
            seen.add(g)
            deduped.append(g)
    return deduped[:4]


def search_google_books(query):
    """
    Secondary API Search: Search Google Books API for books to import into the library.
    Returns results formatted identically to Open Library search with import_token.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("enter a title or author to search")
    query = query.strip()
    if len(query) > 120:
        raise ValueError("search must be at most 120 characters")
    
    params = urlencode({"q": query, "maxResults": 10})
    req = Request(f"{GOOGLE_BOOKS_API}?{params}", headers={"User-Agent": "TheReadingRoom/1.0 (educational library project)"})
    try:
        with urlopen(req, timeout=6) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        raise ConnectionError("Google Books API is unavailable. Try again later or search with Open Library.") from exc

    if not isinstance(payload, dict):
        raise ConnectionError("Google Books API returned an unexpected response.")

    items = payload.get("items", [])
    if not isinstance(items, list):
        return []

    from app.services.open_library import _signer
    results = []
    for item in items:
        if not isinstance(item, dict):
            continue
        volume_id = item.get("id")
        volume_info = item.get("volumeInfo", {})
        title = volume_info.get("title")
        if not volume_id or not isinstance(title, str) or not title.strip():
            continue
        
        authors_list = volume_info.get("authors") or []
        author = ", ".join(authors_list[:3]) if isinstance(authors_list, list) else ""
        
        img_links = volume_info.get("imageLinks") or {}
        cover = img_links.get("thumbnail") or img_links.get("smallThumbnail") or "catalog-placeholder.svg"
        if cover.startswith("http://"):
            cover = "https://" + cover[7:]
        
        page_count = volume_info.get("pageCount")
        pages = page_count if isinstance(page_count, int) and 0 < page_count <= 100000 else None
        
        raw_cats = volume_info.get("categories") or []
        cat_str = " ".join(raw_cats).casefold() + " " + title.casefold()
        if "manga" in cat_str or "manhwa" in cat_str:
            category = "Manga"
        elif "graphic novel" in cat_str:
            category = "Graphic Novels"
        elif "comic" in cat_str or "superhero" in cat_str:
            category = "Comics"
        elif "magazine" in cat_str or "periodical" in cat_str:
            category = "Magazines"
        elif any(w in cat_str for w in ("novel", "fiction", "fantasy", "mystery", "sci-fi")):
            category = "Novels"
        else:
            category = "Literature"
            
        genres = draft_genre_tags_for_book(
            title=title,
            author=author,
            category=category,
            description=volume_info.get("description", ""),
            provider="googlebooks"
        )
        
        pub_date = volume_info.get("publishedDate", "")
        year_match = re.search(r"\b(19\d\d|20\d\d)\b", pub_date)
        first_publish_year = int(year_match.group(1)) if year_match else None

        source_key = f"/googlebooks/{volume_id}"
        data = {
            "source_key": source_key,
            "title": title.strip()[:300],
            "author": author[:300] or "Unknown author",
            "cover": cover,
            "total_units": pages,
            "category": category,
            "genres": genres,
        }
        results.append({
            **data,
            "first_publish_year": first_publish_year,
            "provider": "googlebooks",
            "import_token": _signer().dumps(data),
        })

    return results


def draft_genre_tags_for_book(title, author="", category="", description="", subjects=None, provider="openlibrary", offline_only=False):
    """
    Drafts accurate genre tags for a book title.
    Primary API: Open Library (subjects & taxonomy).
    Secondary API: Google Books (volume categories & description).
    Toggleable via the provider parameter ('openlibrary' vs 'googlebooks').
    Guarantees a clean, non-empty list of 1-4 canonical genre tags.
    When offline_only=True, skips outbound network calls and infers genres instantly via heuristic rules.
    """
    genres = []

    if not offline_only:
        if provider == "googlebooks":
            # Secondary API requested first
            try:
                api_genres = fetch_genres_from_google_books(title, author)
                if api_genres:
                    genres.extend(api_genres)
            except Exception:
                pass
            if len(genres) < 2:
                try:
                    ol_genres = fetch_genres_from_open_library(title, author, subjects)
                    for g in ol_genres:
                        if g not in genres:
                            genres.append(g)
                except Exception:
                    pass
        else:
            # Default: Primary API is Open Library
            try:
                ol_genres = fetch_genres_from_open_library(title, author, subjects)
                if ol_genres:
                    genres.extend(ol_genres)
            except Exception:
                pass
            # Fallback to secondary API (Google Books) if few genres retrieved
            if len(genres) < 2:
                try:
                    gb_genres = fetch_genres_from_google_books(title, author)
                    for g in gb_genres:
                        if g not in genres:
                            genres.append(g)
                except Exception:
                    pass

    # Category-specific anchor tag
    cat_lower = (category or "").lower()
    if "manga" in cat_lower and "Manga" not in genres:
        genres.insert(0, "Manga")
    elif "comic" in cat_lower and "Comics" not in genres:
        genres.insert(0, "Comics")
    elif "graphic" in cat_lower and "Graphic Novel" not in genres:
        genres.insert(0, "Graphic Novel")
    elif "magazine" in cat_lower and "Periodical" not in genres:
        genres.insert(0, "Periodical")
    elif "literature" in cat_lower and "Literary Fiction" not in genres:
        genres.insert(0, "Literary Fiction")

    # Inspect title, description, and subjects for keyword matches
    combined = " ".join([
        title or "", author or "", category or "", description or "",
        " ".join(subjects) if isinstance(subjects, list) else ""
    ]).lower()

    for kw, canonical in GENRE_KEYWORD_MAP.items():
        if canonical not in genres and re.search(r"\b" + re.escape(kw) + r"\b", combined):
            genres.append(canonical)
            if len(genres) >= 3:
                break

    # Fallbacks based on category if still empty
    if not genres:
        fallback_map = {
            "Manga": ["Manga", "Action", "Adventure"],
            "Comics": ["Comics", "Superheroes", "Sci-Fi"],
            "Graphic Novels": ["Graphic Novel", "Drama", "Slice of Life"],
            "Novels": ["Fantasy", "Mystery", "Drama"],
            "Literature": ["Literary Fiction", "Classic"],
            "Magazines": ["Periodical", "Arts & Culture", "Design"],
        }
        genres = fallback_map.get(category, ["Fiction", "Literature"])

    # Final cleanup & limit
    seen = set()
    final_genres = []
    for g in genres:
        clean_g = g.strip()
        if clean_g and clean_g not in seen:
            seen.add(clean_g)
            final_genres.append(clean_g)
    
    return final_genres[:4]
