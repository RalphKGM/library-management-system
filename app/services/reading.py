def update_progress(member_id, media_id, position, status):
    raise NotImplementedError("Implement reading progress.")


def get_progress(member_id, media_id):
    raise NotImplementedError("Implement progress lookup.")


def add_bookmark(member_id, media_id, position, note=""):
    raise NotImplementedError("Implement bookmarks.")


def get_bookmarks(member_id, media_id):
    raise NotImplementedError("Implement bookmark lookup.")


def remove_bookmark(member_id, bookmark_id):
    raise NotImplementedError("Implement bookmark removal.")
