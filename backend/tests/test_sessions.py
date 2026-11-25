import hashlib
import os
import unittest
from unittest.mock import patch

from fastapi import Response
from starlette.requests import Request
from werkzeug.security import generate_password_hash

from auth.router import login_endpoint, logout_endpoint
from auth.service import create_session, revoke_session
from src.core.dependencies import get_current_user
from src.core.errors import ApiError


class FakeCursor:
    def __init__(self, row=None):
        self.row = row
        self.calls = []

    def execute(self, query, params=None):
        self.calls.append((query, params))

    def fetchone(self):
        return self.row


def request_with_cookie(token=None, headers=None):
    request_headers = list(headers or [])
    if token:
        request_headers.append((b"cookie", f"bb_session={token}".encode("ascii")))
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/api/private",
        "headers": request_headers,
    })


class SessionTests(unittest.TestCase):
    def test_login_sets_http_only_cookie_and_logout_expires_it(self):
        user = {
            "userid": 7,
            "fullname": "Owner",
            "username": "owner",
            "role": "Owner",
            "password": generate_password_hash("test-password"),
            "isactive": True,
        }
        cur = FakeCursor(row=user)
        response = Response()

        with patch.dict(os.environ, {
            "BB_COOKIE_SECURE": "false",
            "BB_SESSION_TTL_HOURS": "1",
        }):
            result = login_endpoint(
                response,
                cur,
                {"username": "owner", "password": "test-password"},
            )

        self.assertNotIn("password", result)
        set_cookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", set_cookie)
        self.assertIn("SameSite=strict", set_cookie)
        self.assertNotIn("Secure", set_cookie)
        token = set_cookie.split("bb_session=", 1)[1].split(";", 1)[0]
        request = request_with_cookie(token)

        logout_response = logout_endpoint(request, Response(), cur)

        self.assertEqual(logout_response.status_code, 204)
        self.assertIn("Max-Age=0", logout_response.headers["set-cookie"])
        self.assertIn("DELETE FROM app_sessions", cur.calls[-1][0])

    def test_create_and_revoke_session_store_only_token_hash(self):
        cur = FakeCursor()
        with patch.dict(os.environ, {"BB_SESSION_TTL_HOURS": "2"}):
            token, max_age = create_session(cur, 42)

        self.assertEqual(max_age, 7200)
        self.assertGreaterEqual(len(token), 40)
        inserted_query, inserted_params = cur.calls[-1]
        self.assertIn("INSERT INTO app_sessions", inserted_query)
        self.assertEqual(inserted_params[0], hashlib.sha256(token.encode()).hexdigest())
        self.assertNotIn(token, inserted_params)
        self.assertEqual(inserted_params[1:], (42, 2))

        revoke_session(cur, token)
        delete_query, delete_params = cur.calls[-1]
        self.assertIn("DELETE FROM app_sessions", delete_query)
        self.assertEqual(delete_params, (hashlib.sha256(token.encode()).hexdigest(),))

    def test_username_header_does_not_authenticate_without_session_cookie(self):
        cur = FakeCursor()
        request = request_with_cookie(headers=[(b"x-username", b"owner")])

        with self.assertRaises(ApiError) as raised:
            get_current_user(request, cur)

        self.assertEqual(raised.exception.status, 401)
        self.assertEqual(cur.calls, [])

    def test_current_user_looks_up_hashed_cookie_and_active_user(self):
        token = "opaque-session-token"
        user = {"userid": 7, "fullname": "Owner", "username": "owner", "role": "Owner"}
        cur = FakeCursor(row=user)

        result = get_current_user(request_with_cookie(token), cur)

        self.assertEqual(result, user)
        query, params = cur.calls[0]
        self.assertIn("s.expires_at > CURRENT_TIMESTAMP", query)
        self.assertIn("u.isactive", query)
        self.assertEqual(params, (hashlib.sha256(token.encode()).hexdigest(),))

    def test_invalid_or_expired_session_is_rejected(self):
        cur = FakeCursor(row=None)

        with self.assertRaises(ApiError) as raised:
            get_current_user(request_with_cookie("expired-token"), cur)

        self.assertEqual(raised.exception.status, 401)
