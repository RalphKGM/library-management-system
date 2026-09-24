def filter_by_category(items, category):
    return [item for item in items if item["category"] == category]


def sort_by_title(items):
    return sorted(items, key=lambda item: item["title"].casefold())


def calculate_progress(current_position, total_units):
    if type(current_position) is not int or current_position < 0:
        raise ValueError("current position must be nonnegative")
    if total_units is None:
        return None
    if type(total_units) is not int or total_units <= 0 or current_position > total_units:
        raise ValueError("invalid total or position")
    return round(current_position / total_units * 100)
