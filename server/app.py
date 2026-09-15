"""Small WSGI application. Use a production WSGI server behind HTTPS for deployment."""

import json
import mimetypes
import os
import time
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from wsgiref.simple_server import make_server
from server.mail import MailUnavailable, send_request
from server.validation import validate

ROOT = Path(__file__).resolve().parent.parent
MAX_BODY = 24000
HEADERS = [
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
    (
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self' https://request-site-6jmpix9dl-aero-forger.vercel.app; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
    ),
]


class RateLimiter:
    def __init__(self, limit=5, window=900, capacity=10000):
        self.limit, self.window, self.capacity = limit, window, capacity
        self.entries = OrderedDict()
        self.lock = Lock()

    def allow(self, address):
        now = time.monotonic()
        with self.lock:
            while self.entries and next(iter(self.entries.values()))[0] <= now - self.window:
                self.entries.popitem(last=False)
            stamp, count = self.entries.get(address, (now, 0))
            if count >= self.limit:
                return False
            if address not in self.entries and len(self.entries) >= self.capacity:
                return False
            self.entries[address] = (stamp, count + 1)
            return True


limiter = RateLimiter()


def json_response(start_response, code, data, extra=None):
    body = json.dumps(data).encode()
    start_response(
        code,
        HEADERS
        + [
            ("Content-Type", "application/json"),
            ("Cache-Control", "no-store"),
            ("Content-Length", str(len(body))),
        ]
        + (extra or []),
    )
    return [body]


def application(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET")
    if path == "/api/requests":
        origin = environ.get("HTTP_ORIGIN")
        allowed = os.environ.get(
            "SITE_ORIGIN",
            "https://request-site-6jmpix9dl-aero-forger.vercel.app"
            if os.environ.get("VERCEL")
            else "http://localhost:3000",
        ).rstrip("/")
        allowed_origins = {
            allowed,
            "https://request-site-6jmpix9dl-aero-forger.vercel.app",
            "https://request-site-tan.vercel.app",
            "https://request-site-aero-forger.vercel.app",
        }
        original_start_response = start_response

        def start_response(status, headers):
            headers = headers + [("Vary", "Origin")]
            if origin in allowed_origins:
                headers += [("Access-Control-Allow-Origin", origin)]
            return original_start_response(status, headers)

        if method == "OPTIONS":
            requested_headers = {
                header.strip().lower()
                for header in environ.get("HTTP_ACCESS_CONTROL_REQUEST_HEADERS", "").split(",")
                if header.strip()
            }
            if (
                origin not in allowed_origins
                or environ.get("HTTP_ACCESS_CONTROL_REQUEST_METHOD") != "POST"
                or requested_headers - {"content-type"}
            ):
                return json_response(
                    start_response, "403 Forbidden", {"error": "Origin or method not allowed."}
                )
            start_response(
                "204 No Content",
                HEADERS
                + [
                    ("Access-Control-Allow-Methods", "POST"),
                    ("Access-Control-Allow-Headers", "Content-Type"),
                    ("Access-Control-Max-Age", "600"),
                    ("Content-Length", "0"),
                ],
            )
            return []

        def reply(code, error, extra=None):
            return json_response(start_response, code, {"error": error}, extra)

        if method != "POST":
            return reply(
                "405 Method Not Allowed", "Use POST to submit a request.", [("Allow", "POST")]
            )
        if not limiter.allow(environ.get("REMOTE_ADDR", "unknown")):
            return reply(
                "429 Too Many Requests",
                "Too many attempts. Please try again in 15 minutes.",
                [("Retry-After", "900")],
            )
        if (origin and origin not in allowed_origins) or (
            not origin and environ.get("HTTP_SEC_FETCH_SITE") == "cross-site"
        ):
            return reply("403 Forbidden", "Requests must be submitted from this website.")
        if environ.get("CONTENT_TYPE", "").split(";")[0].strip().lower() != "application/json":
            return reply("415 Unsupported Media Type", "Send a JSON request.")
        try:
            length = int(environ.get("CONTENT_LENGTH", ""))
        except ValueError:
            return reply("400 Bad Request", "Invalid request length.")
        if length > MAX_BODY:
            return reply("413 Content Too Large", "Request is too large.")
        if length <= 0:
            return reply("400 Bad Request", "Request body is required.")
        try:
            raw = environ["wsgi.input"].read(length)
            if len(raw) != length:
                return reply("400 Bad Request", "Incomplete request body.")
            data = validate(json.loads(raw))
        except (ValueError, UnicodeError) as error:
            message = (
                str(error)
                if not isinstance(error, (json.JSONDecodeError, UnicodeError))
                else "Malformed JSON request."
            )
            return reply("400 Bad Request", message)
        try:
            send_request(data)
        except MailUnavailable:
            return reply(
                "503 Service Unavailable",
                "Email is temporarily unavailable. Your details are still in the form; please try again later.",
            )
        return json_response(
            start_response,
            "201 Created",
            {"message": "Request sent. I'll contact you if I'm interested."},
        )
    if path.startswith("/api/"):
        return json_response(start_response, "404 Not Found", {"error": "Endpoint not found."})
    if method not in ("GET", "HEAD"):
        return json_response(
            start_response,
            "405 Method Not Allowed",
            {"error": "Method not allowed."},
            [("Allow", "GET, HEAD")],
        )
    public = ROOT / ("dist" if (ROOT / "dist/index.html").exists() else "public")
    file = (public / ("index.html" if path == "/" else path.lstrip("/"))).resolve()
    if not file.is_relative_to(public.resolve()) or not file.is_file():
        return json_response(start_response, "404 Not Found", {"error": "Page not found."})
    body = file.read_bytes()
    content_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
    start_response(
        "200 OK",
        HEADERS
        + [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-cache"),
        ],
    )
    return [body] if method == "GET" else []


def load_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_env()
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "3000"))
    with make_server("0.0.0.0", port, application) as server:
        print(f"AeroForger running at http://localhost:{port}", flush=True)
        server.serve_forever()
