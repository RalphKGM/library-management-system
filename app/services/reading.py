def update_progress(member_id, media_id, position, status):
    """Validate and save one progress record per member and title."""
    raise NotImplementedError("Implement reading progress.")


def get_progress(member_id, media_id):
    """Retrieve saved reading progress."""
    raise NotImplementedError("Implement progress lookup.")


def add_bookmark(member_id, media_id, position, note=""):
    """Validate and save a page or chapter bookmark."""
    raise NotImplementedError("Implement bookmarks.")


def get_bookmarks(member_id, media_id):
    """Retrieve a member's bookmarks for a title."""
    raise NotImplementedError("Implement bookmark lookup.")


def remove_bookmark(member_id, bookmark_id):
    """Check ownership before removing the bookmark."""
    raise NotImplementedError("Implement bookmark removal.")
