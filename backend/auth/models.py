from typing import Any, TypedDict


class UserRow(TypedDict, total=False):
    userid: int
    fullname: str
    username: str
    role: str
    password: str
    isactive: bool
