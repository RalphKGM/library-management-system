import csv
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "instance" / "library.sqlite3"
OUTPUT = ROOT / "data"


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    books = db.execute(
        "SELECT m.media_id, m.title, m.author, m.category, m.source_key, m.cover, "
        "COUNT(c.copy_id) AS copies "
        "FROM media_item m LEFT JOIN media_copy c ON c.media_id = m.media_id "
        "GROUP BY m.media_id ORDER BY m.category, m.title"
    ).fetchall()
    members = db.execute(
        "SELECT full_name, username FROM member WHERE username LIKE 'demo_reader_%' "
        "ORDER BY username"
    ).fetchall()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT / "demo_books.csv",
              ("title", "author", "category", "copies", "open_library_url", "cover_url"),
              ({
                  "title": row["title"], "author": row["author"],
                  "category": row["category"], "copies": row["copies"],
                  "open_library_url": f"https://openlibrary.org{row['source_key']}" if row["source_key"] else "",
                  "cover_url": row["cover"] if row["cover"].startswith("https://") else "",
              } for row in books))
    write_csv(OUTPUT / "demo_members.csv", ("full_name", "username"),
              (dict(row) for row in members))
    print(f"Exported {len(books)} books and {len(members)} demo members")


if __name__ == "__main__":
    main()
