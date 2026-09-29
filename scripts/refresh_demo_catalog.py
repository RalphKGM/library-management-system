import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "app" / "data" / "demo_open_library.json"
USER_AGENT = "TheReadingRoom/1.0 (educational library project)"
PICKS = {
    "Manga": ("manga", [
        "OL5769568W", "OL11766231W", "OL8755973W", "OL8756038W",
        "OL8756227W", "OL13738065W", "OL8211773W", "OL8756324W",
        "OL19719004W", "OL5750784W", "OL8752654W", "OL8400751W",
    ]),
    "Comics": ("comics", [
        "OL17342469W", "OL276032W", "OL25886W", "OL8842598W",
        "OL20666248W", "OL21337755W", "OL19659659W", "OL20757578W",
        "OL2756365W", "OL17623120W", "OL1818513W", "OL20659134W",
    ]),
    "Literature": ("literature", [
        "OL53908W", "OL9170454W", "OL8193478W", "OL450063W",
        "OL66562W", "OL8193465W", "OL24034W", "OL85892W",
        "OL29983W", "OL258902W", "OL258850W", "OL20600W",
    ]),
    "Novels": ("novels", [
        "OL5735363W", "OL40873W", "OL11999891W", "OL50565W",
        "OL15168588W", "OL38501W", "OL20150260W", "OL19781733W",
        "OL88877W", "OL26398W", "OL138395W", "OL77840W",
    ]),
    "Magazines": ("magazine", [
        "OL17806219W", "OL24142686W", "OL9879446W", "OL42472009W",
        "OL20209121W", "OL20239868W", "OL20321810W", "OL24313606W",
        "OL19910865W", "OL19914271W", "OL19634963W", "OL20239923W",
    ]),
    "Graphic Novels": ("graphic_novels", [
        "OL2056818W", "OL267622W", "OL267610W", "OL151056W",
        "OL151051W", "OL267607W", "OL267617W", "OL267624W",
        "OL267613W", "OL151078W", "OL2694991W", "OL258893W",
    ]),
}


def main():
    books = []
    used = set()
    for category, (subject, keys) in PICKS.items():
        url = f"https://openlibrary.org/subjects/{subject}.json?limit=100"
        with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=20) as response:
            works = json.load(response)["works"]
        by_key = {work.get("key"): work for work in works}
        for key in keys:
            source_key = f"/works/{key}"
            work = by_key.get(source_key)
            if work is None:
                raise ValueError(f"Open Library did not return {source_key} for {category}")
            if source_key in used:
                raise ValueError(f"work selected twice: {source_key}")
            authors = [author.get("name", "") for author in work.get("authors", [])]
            cover_id = work.get("cover_id")
            if not work.get("title") or not authors or type(cover_id) is not int:
                raise ValueError(f"incomplete Open Library record: {source_key}")
            used.add(source_key)
            books.append({
                "category": category,
                "source_key": source_key,
                "source_url": f"https://openlibrary.org{source_key}",
                "title": work["title"][:300],
                "author": ", ".join(authors[:3])[:300],
                "cover": f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg",
                "first_publish_year": work.get("first_publish_year"),
            })
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({
        "source": "Open Library Subjects API",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "books": books,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(books)} Open Library records to {OUTPUT}")


if __name__ == "__main__":
    main()
