from dataclasses import dataclass
from typing import Optional


# record containers only; persistence and validation are not implemented.
@dataclass
class Member:
    member_id: int
    full_name: str
    username: str
    password_hash: str
    registered_at: str
    role: str = "member"

    def to_dict(self, include_password: bool = False) -> dict:
        data = {
            "member_id": self.member_id,
            "full_name": self.full_name,
            "username": self.username,
            "role": self.role,
            "registered_at": self.registered_at,
        }
        if include_password:
            data["password_hash"] = self.password_hash
        return data


@dataclass
class MediaItem:
    media_id: int
    title: str
    author: str
    category: str
    volume: Optional[str] = None
    progress_unit: str = "page"
    total_units: Optional[int] = None


@dataclass
class MediaCopy:
    copy_id: int
    media_id: int
    accession_number: str


@dataclass
class BorrowingRecord:
    borrowing_id: int
    member_id: int
    copy_id: int
    borrowed_at: str
    returned_at: Optional[str] = None


@dataclass
class ReadingProgress:
    progress_id: int
    member_id: int
    media_id: int
    current_position: int
    status: str
    updated_at: str


@dataclass
class Bookmark:
    bookmark_id: int
    member_id: int
    media_id: int
    position: int
    created_at: str
    note: str = ""
