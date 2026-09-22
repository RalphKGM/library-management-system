# Tests to write during implementation

- Registered member can borrow an available copy.
- Unknown member cannot borrow a copy.
- Two simultaneous requests cannot borrow the same copy.
- A return makes the copy available; a repeated return is rejected.
- Duplicate usernames and accession numbers are rejected.
- Reading progress is unique per member and title.
- Page or chapter positions cannot be negative or exceed a known total.
- A member cannot change another member's bookmarks or progress.
- Password verification and librarian permissions are enforced.
- Pure helper functions leave input collections unchanged.

No feature tests or completed feature implementations are included yet.
