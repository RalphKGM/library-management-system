def register_member(full_name, username, password):
    """Validate details, hash the password, and save a member."""
    raise NotImplementedError("Implement member registration.")


def authenticate_member(username, password):
    """Check credentials without exposing password hashes."""
    raise NotImplementedError("Implement member authentication.")


def get_member(member_id):
    """Retrieve a registered member."""
    raise NotImplementedError("Implement member lookup.")
