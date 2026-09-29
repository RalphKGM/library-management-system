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
    total_units INTEGER,
    description TEXT NOT NULL DEFAULT '',
    cover TEXT NOT NULL DEFAULT 'catalog-placeholder.svg',
    added_at TEXT NOT NULL DEFAULT '',
    source_key TEXT UNIQUE
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

CREATE UNIQUE INDEX IF NOT EXISTS one_active_borrowing_per_copy
ON borrowing_record (copy_id) WHERE returned_at IS NULL;

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

CREATE TABLE IF NOT EXISTS notification (
    notification_id INTEGER PRIMARY KEY,
    recipient_role TEXT NOT NULL CHECK (recipient_role IN ('member', 'librarian')),
    recipient_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    target TEXT NOT NULL,
    created_at TEXT NOT NULL,
    read_at TEXT
);

CREATE INDEX IF NOT EXISTS notification_inbox
ON notification (recipient_role, recipient_id, read_at, notification_id DESC);

CREATE TABLE IF NOT EXISTS genre (
    genre_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS media_genre (
    media_id INTEGER NOT NULL REFERENCES media_item(media_id) ON DELETE CASCADE,
    genre_id INTEGER NOT NULL REFERENCES genre(genre_id) ON DELETE CASCADE,
    PRIMARY KEY (media_id, genre_id)
);

CREATE INDEX IF NOT EXISTS idx_media_genre_genre ON media_genre (genre_id);
