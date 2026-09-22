def add_media(details):
    """Validate and save title, author, category, and volume details."""
    raise NotImplementedError("Implement media creation.")


def update_media(media_id, changes):
    """Validate and update an existing title."""
    raise NotImplementedError("Implement media updates.")


def search_media(query="", category=None):
    """Find titles using the supplied search criteria."""
    raise NotImplementedError("Implement media search.")


def add_copy(media_id, accession_number):
    """Register an individual physical copy."""
    raise NotImplementedError("Implement copy registration.")


def get_available_copies(media_id):
    """Find copies without an active borrowing record."""
    raise NotImplementedError("Implement availability lookup.")
