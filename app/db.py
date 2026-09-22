def get_db():
    """Open a request-scoped SQLite connection with foreign keys enabled."""
    raise NotImplementedError("Implement the SQLite connection.")


def close_db(error=None):
    """Close the request connection during Flask teardown."""
    raise NotImplementedError("Implement connection cleanup.")


def init_db():
    """Create the instance directory and apply schema.sql explicitly."""
    raise NotImplementedError("Implement database initialization.")
