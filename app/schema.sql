PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS member (
    member_id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    registered_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS librarian (
    librarian_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS media_item (
    media_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    category TEXT NOT NULL,
    volume TEXT,
    progress_unit TEXT NOT NULL,
    total_units INTEGER
);

CREATE TABLE IF NOT EXISTS media_copy (
    copy_id INTEGER PRIMARY KEY,
    media_id INTEGER NOT NULL REFERENCES media_item(media_id),
    accession_number TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS borrowing_record (
    borrowing_id INTEGER PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES member(member_id),
    copy_id INTEGER NOT NULL REFERENCES media_copy(copy_id),
    borrowed_at TEXT NOT NULL,
    returned_at TEXT
);

CREATE TABLE IF NOT EXISTS reading_progress (
    progress_id INTEGER PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES member(member_id),
    media_id INTEGER NOT NULL REFERENCES media_item(media_id),
    current_position INTEGER NOT NULL,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (member_id, media_id)
);

CREATE TABLE IF NOT EXISTS bookmark (
    bookmark_id INTEGER PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES member(member_id),
    media_id INTEGER NOT NULL REFERENCES media_item(media_id),
    position INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

-- todo: enforce only one unreturned borrowing per copy.
-- todo: validate nonnegative positions and supported progress/status values.
