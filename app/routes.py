from flask import Blueprint

api = Blueprint("api", __name__, url_prefix="/api")


@api.get("/health")
def health():
    return {"status": "ok"}


# todo: add routes after implementing the corresponding service functions.
# planned: /members, /media, /copies, /borrowings, /progress, /bookmarks
# todo: validate requests and enforce member/librarian permissions.
# todo: return suitable HTTP status codes for missing or invalid records.
