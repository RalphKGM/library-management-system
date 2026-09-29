import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app
from app.services.members import create_librarian


def main():
    output = ROOT / "dist" / "library-demo-windows.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        package = Path(folder) / "library-demo"
        package.mkdir()
        shutil.copytree(
            ROOT / "app", package / "app",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )
        for filename in ("requirements.txt", "run_demo.py", "WINDOWS_DEMO_README.txt"):
            shutil.copy2(ROOT / filename, package / filename)
        batch = (ROOT / "run-demo.bat").read_text(encoding="utf-8")
        (package / "run-demo.bat").write_bytes(batch.replace("\n", "\r\n").encode("utf-8"))
        database = package / "instance" / "library.sqlite3"
        database.parent.mkdir()
        app = create_app({"DATABASE": str(database), "TESTING": True})
        with app.app_context():
            create_librarian("demo_staff", "DemoStaff2026!")
        result = app.test_cli_runner().invoke(args=["seed-demo"])
        if result.exit_code:
            raise RuntimeError(result.output) from result.exception
        with sqlite3.connect(database) as db:
            books = db.execute("SELECT COUNT(*) FROM media_item").fetchone()[0]
            members = db.execute("SELECT COUNT(*) FROM member").fetchone()[0]
            categories = db.execute(
                "SELECT category, COUNT(*) FROM media_item GROUP BY category"
            ).fetchall()
            if books != 60 or members != 10 or len(categories) != 6 or any(count != 10 for _, count in categories):
                raise RuntimeError("Demo database counts are incomplete")
        with ZipFile(output, "w", ZIP_DEFLATED) as archive:
            for path in package.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(package.parent))
    print(f"Created {output}")
    print("Included 60 books, 10 members, and demo_staff")


if __name__ == "__main__":
    main()
