def borrow_copy(member_id, copy_id):
    """Check membership and availability, then record borrowing atomically."""
    raise NotImplementedError("Implement borrowing without a fee.")


def return_copy(borrowing_id):
    """Validate an active borrowing and record its return time."""
    raise NotImplementedError("Implement returns.")


def get_borrowing_history(member_id):
    """Retrieve a member's current and past borrowings."""
    raise NotImplementedError("Implement borrowing history.")
