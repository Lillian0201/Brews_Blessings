from typing import Any

from pydantic import BaseModel


class UserRequest(BaseModel):
    name: Any = None
    username: Any = None
    role: Any = None
    password: Any = None
    active: Any = None
