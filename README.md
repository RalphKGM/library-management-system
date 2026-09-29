# Entertainment Media Library Management System

**Group 2 | Principles of Programming Languages &bull; Section AM5**  
**Course Instructor:** Jefferson Costales &nbsp;|&nbsp; **Date:** September 29, 2026  

---

## 👥 Team Member Contributions

| Team Member (Full Name) | Assigned Role | Key Contributions & Technical Deliverables |
| :--- | :--- | :--- |
| **Jermaine Van Danganan** | **System Design & Advanced Integrations** | &bull; Multi-tier system architecture, Level 1 & Level 2 Data Flow Diagrams (DFDs), and UML Use-Case design.<br>&bull; Google Books secondary API integration with provider dropdown toggle.<br>&bull; Automated genre taxonomy classifier and relational normalization engine.<br>&bull; Staff circulation analytics sheets engine and 100% Bootstrap Icons migration. |
| **Ralph Kevin Morales** | **Core Implementation & Open Library** | &bull; Remote Git repository implementation, Flask routing, and Jinja2 templates.<br>&bull; Open Library API search, cover image fetching, and subject import pipeline.<br>&bull; Baseline catalog browsing, member/staff views, and core relational models.<br>&bull; Session management, security role boundaries, and physical copy generation. |
| **Gerard Raphael Cruz** | **Backend & ERD Design** | &bull; Entity-Relationship Diagram (ERD) schema design and relational integrity constraints.<br>&bull; Core circulation business logic (borrowing, return validations, stock updates).<br>&bull; Concurrency guards against duplicate active borrowings (`one_active_borrowing_per_copy`).<br>&bull; Member reading tracker progress calculations and persistent bookmarks. |
| **Niel Francis Arligue** | **Documentation, Testing & Level 0 DFD** | &bull; Level 0 Data Flow Diagram (Context-level external boundaries and process flow).<br>&bull; Comprehensive technical project documentation and Markdown specifications.<br>&bull; Slide presentation authoring and formatting in Marp.<br>&bull; Systematic test suite execution, edge-case validation, and verification reporting. |

---

## 📖 Project Overview

The **Entertainment Media Library Management System** is a modular web application written in Python 3.12, Flask, Jinja2, and SQLite3. It is designed to manage physical collections of manga, comics, graphic novels, novels, magazines, and literature.

### Key Highlights
- **Dual External API Ingestion Engine**:
  - **Open Library (Primary API)**: Bibliographic search, book cover CDNs, subject taxonomies, and default genre classification.
  - **Google Books (Secondary API)**: Accessible via a live **UI dropdown toggle**, fetching volume categories, thumbnails, and descriptions.
- **Automated Genre Taxonomy & Normalization**: An automated classifier extracts and normalizes external subject tags into canonical genres stored in dedicated SQLite relational tables (`genre`, `media_genre`).
- **Staff Circulation Analytics Sheets**: Dedicated analytics workspaces summarizing:
  1. *Top Genres Borrowed* (borrow counts, active loans, and volume share %).
  2. *Top Book Types Borrowed* (turnover circulation rates and category shares).
  3. *Book Borrowing Leaderboard* (lifetime loan rankings with podium medals 🥇, 🥈, 🥉).
- **Concurrency & State Invariants**: Enforces database-level constraints preventing double-borrowing of the same physical copy (`one_active_borrowing_per_copy`).
- **Member Workspace & Reading Tracker**: Allows members to borrow physical copies for free, track reading progress percentages (by page or chapter), and save bookmarks with personal notes.
- **Modern Aesthetic**: 100% Bootstrap Icons vector iconography replacing legacy unicode symbols, responsive layouts, and print-ready documentation.

---

## 💡 Applied Principles of Programming Languages (PPL)

The system exemplifies seven foundational concepts required by the course syllabus:

| # | PPL Concept | Source Module | Technical Implementation |
|---|---|---|---|
| **1** | **Classes & Objects** | `models.py` | Strongly-typed domain models defined with Python `@dataclass` schemas (`MediaItem`, `MediaCopy`, `Member`, `GenreRanking`). |
| **2** | **Validation & Data Integrity** | `borrowing.py` | Defensive validation checking member existence, copy availability, and duplicate loan prevention with atomic SQLite partial unique index. |
| **3** | **Collections & Data Structures** | `analytics.py` | Aggregating database rows into structured ranking collections with calculated borrow share percentages and dictionary mapping. |
| **4** | **Functions & Methods** | `media.py` | Cohesive, single-responsibility service functions (`set_media_genres`, `create_media_item`, `get_or_create_genre`) ensuring modularity. |
| **5** | **Control Structures** | `routes.py` | Deterministic conditional branching dynamically selecting between Open Library and Google Books API handlers based on user choice. |
| **6** | **Exception Handling** | `google_books.py` | Trapping socket timeouts (`HTTPError`, `URLError`, `TimeoutError`) safely to isolate network failures and degrade gracefully to heuristics. |
| **7** | **Functional Programming** | `helpers.py` | Pure, referentially transparent mathematical calculation (`calculate_progress`) with zero side-effects or state mutation. |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9 or newer (Python 3.12 recommended)
- Git

### Local Execution (Windows PowerShell)

```powershell
# 1. Create and activate a virtual environment
py -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install dependencies
python -m pip install -r requirements.txt

# 3. Initialize the SQLite database
python -m flask --app app init-db

# 4. Seed the demo catalog & demo members (optional)
python -m flask --app app seed-demo

# 5. Run the development server
python -m flask --app app run --debug
```

Open your browser to: **`http://127.0.0.1:5000/`**

### Local Execution (macOS / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m flask --app app init-db
python -m flask --app app seed-demo
python -m flask --app app run --debug
```

### Run with Docker Compose

```bash
docker compose up -d --build
```
Open **`http://127.0.0.1:5001/`** in your browser. (The SQLite database persists in the mapped volume).

---

## 🔑 Demo Credentials

| Role | Username | Password | Purpose |
| :--- | :--- | :--- | :--- |
| **Librarian / Staff** | `demo_staff` | `DemoStaff2026!` | Catalog management, API ingestion, circulation sheets, physical copies |
| **Member / Reader** | `demo_reader_01` &ndash; `demo_reader_10` | `DemoReader2026!` | Catalog browsing, borrowing physical copies, reading tracker, bookmarks |

> *To manually create a custom staff account via CLI:*
> ```powershell
> python -m flask --app app create-librarian
> ```

---

## 📊 System Architecture & Diagrams

The complete architecture and design specifications are documented with clean vector diagrams:

- **Tier Architecture (C4 Model)**: 4 distinct architectural tiers (Client UI, Gateway & Security, Domain Services, Persistence & APIs).
- **Level 0 Data Flow Diagram (DFD)**: Context-level boundaries connecting Member, Librarian, Open Library, and Google Books.
- **Level 1 Data Flow Diagram (DFD)**: System decomposition across 6 core processes (`1.0` Auth, `2.0` Search, `3.0` Ingestion, `4.0` Circulation, `5.0` Reading Tracker, `6.0` Analytics Sheets).
- **Level 2 Data Flow Diagram (DFD)**: Process `3.0` decomposition detailing provider dispatch, 5s timeout guard, taxonomy classifier, and relational persistence.
- **UML Use-Case Diagram**: Role-based access boundaries separating Guests, Members, and Librarians.
- **Entity Relationship Diagram (ERD)**: Complete normalized relational schema with junction tables and unique constraints.

All vector diagrams are available in the project artifacts directory:
- `_local_artifacts/diagrams/dfd_level0.svg`
- `_local_artifacts/diagrams/dfd_level1.svg`
- `_local_artifacts/diagrams/dfd_level2.svg`
- `_local_artifacts/diagrams/use_case.svg`
- `_local_artifacts/diagrams/tier_architecture.svg`

---

## 🧪 Automated Testing

Execute the automated test suite covering authentication, permissions, CSRF guards, loan invariant checks, and API routes:

```bash
python -m unittest discover -s tests -v
```

---

## 📁 Project Structure

```text
app/
  __init__.py           # Flask app factory, session configuration, error handlers
  db.py                 # SQLite connection manager, schema initialization, CLI commands
  schema.sql            # Relational database tables, indexes, and loan invariants
  security.py           # Session identity, RBAC checks, password hashing, and CSRF tokens
  routes.py             # RESTful JSON API endpoints
  ui.py                 # Jinja2 template views and form handling
  models.py             # Strongly-typed dataclass domain models
  services/             # Cohesive, single-responsibility business logic services
    analytics.py        # Staff circulation sheets aggregation engines
    borrowing.py        # Borrowing, returning, and concurrency invariant checks
    google_books.py     # Google Books API integration and category extraction
    helpers.py          # Pure mathematical calculations (reading progress)
    media.py            # Media catalog CRUD and genre taxonomy assignment
    members.py          # Member registration and profile management
    notifications.py    # In-app notifications and loan alerts
    open_library.py     # Open Library API search, ingestion, and genre drafting
    reading.py          # Reading progress tracker and bookmark persistence
  templates/            # Jinja2 HTML templates styled with Bootstrap Icons
  static/               # CSS styles, JavaScript handlers, and SVG placeholders
tests/
  test_app.py           # Comprehensive integration and role-based test suite
```

---

## 📑 Project Documentation & Presentation Deck

- **Website Documentation (Markdown)**: `_local_artifacts/DOCUMENTATION.md`
- **Print-Ready Documentation (HTML)**: `_local_artifacts/documentation.html` (Press `Ctrl+P` to save as formatted PDF)
- **Marp Presentation Slide Deck**: `_local_artifacts/presentation.md` (Run with `@marp-team/marp-cli` or open in Marp extension)
