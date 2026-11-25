from typing import Any

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: Any = None
    password: Any = None
