import io
import json
import unittest
from unittest.mock import patch
from server import app
from server.mail import MailUnavailable, send_request
from server.validation import validate

VALID = {
    "type": "desktop",
    "name": "Example App",
    "description": "A small desktop application for organizing local files.",
    "email": "client@example.com",
    "budget": "",
}


class ApiTests(unittest.TestCase):
    def setUp(self):
        app.limiter = app.RateLimiter()

    def request(self, payload=VALID, method="POST", **overrides):
        body = json.dumps(payload).encode()
        env = {
            "PATH_INFO": "/api/requests",
            "REQUEST_METHOD": method,
            "REMOTE_ADDR": "127.0.0.1",
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
        }
        env.update(overrides)
        result = {}

        def start(status, headers):
            result["status"] = int(status.split()[0])
            result["headers"] = dict(headers)

        result["body"] = json.loads(b"".join(app.application(env, start)))
        return result

    @patch("server.app.send_request")
    def test_valid_request(self, mail):
        result = self.request()
        self.assertEqual(result["status"], 201)
        mail.assert_called_once()
        self.assertEqual(mail.call_args.args[0]["email"], "client@example.com")

    def test_rejects_bad_fields(self):
        for change in [
            {"email": "bad"},
            {"email": "x@example.com\r\nBcc: bad@example.com"},
            {"description": "short"},
            {"name": "x" * 101},
            {"type": "unknown"},
            {"budget": 4},
            {"to": "attacker@example.com"},
            {"website": "spam"},
        ]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate({**VALID, **change})
        for value in [[], None, "text"]:
            with self.assertRaises(ValueError):
                validate(value)

    def test_malformed_and_size(self):
        self.assertEqual(
            self.request(**{"wsgi.input": io.BytesIO(b"{"), "CONTENT_LENGTH": "1"})["status"], 400
        )
        self.assertEqual(self.request(CONTENT_LENGTH="25000")["status"], 413)
        self.assertEqual(self.request(CONTENT_TYPE="text/plain")["status"], 415)
        self.assertEqual(self.request(method="GET")["status"], 405)

    def test_origin(self):
        self.assertEqual(self.request(HTTP_ORIGIN="https://evil.example")["status"], 403)

    @patch("server.app.send_request", side_effect=MailUnavailable("secret detail"))
    def test_failure_is_private(self, mail):
        result = self.request()
        self.assertEqual(result["status"], 503)
        self.assertNotIn("secret", str(result))

    @patch("server.app.send_request")
    def test_rate_limit(self, mail):
        for _ in range(5):
            self.request()
        result = self.request()
        self.assertEqual(result["status"], 429)
        self.assertEqual(result["headers"]["Retry-After"], "900")
        self.assertEqual(mail.call_count, 5)

    @patch.dict(
        "os.environ",
        {
            "RESEND_API_KEY": "test",
            "MAIL_FROM": "sender@example.com",
            "REQUEST_TO": "owner@example.com",
        },
    )
    @patch("server.mail.urlopen")
    def test_mail_has_fixed_recipient_and_reply_to(self, urlopen):
        urlopen.return_value.__enter__.return_value = io.BytesIO(b'{"id":"test-message"}')
        send_request(validate(VALID))
        message = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(message["to"], ["owner@example.com"])
        self.assertEqual(message["from"], "sender@example.com")
        self.assertEqual(message["reply_to"], VALID["email"])
        self.assertIn("Budget: Not specified", message["text"])
        self.assertNotIn("html", message)

    def test_limiter_expiration_and_capacity(self):
        limiter = app.RateLimiter(limit=1, window=10, capacity=1)
        with patch("server.app.time.monotonic", return_value=1):
            self.assertTrue(limiter.allow("a"))
            self.assertFalse(limiter.allow("a"))
            self.assertFalse(limiter.allow("b"))
        with patch("server.app.time.monotonic", return_value=12):
            self.assertTrue(limiter.allow("b"))

    def test_private_files_not_served(self):
        for path in ["/../.env.example", "/server/mail.py", "/.env"]:
            statuses = []
            app.application(
                {"PATH_INFO": path, "REQUEST_METHOD": "GET"},
                lambda status, headers: statuses.append(status),
            )
            self.assertEqual(statuses, ["404 Not Found"])


if __name__ == "__main__":
    unittest.main()
