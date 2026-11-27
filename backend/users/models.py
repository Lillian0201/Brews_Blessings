from typing import TypedDict


ROLES = ("Owner", "Barista", "Admin")


class UserRow(TypedDict, total=False):
    userid: int
    fullname: str
    username: str
    role: str
    isactive: bool
