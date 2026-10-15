"""A real localhost HTTP server with fake, in-memory data for Robot tests.

Robot calls the decorated Python methods as readable keywords. Each suite owns
its server; port 0 asks Windows for a free port, avoiding hard-coded port clashes.
This is a teaching mock, not a production web server or authentication system.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse

from robot.api.deco import keyword, library


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Keep HTTP access logs out of Robot's console output."""

    def respond(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            body = (Path(__file__).parent.parent / "web" / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/health":
            self.respond(200, {"status": "ok"})
        elif path == "/api/users":
            self.respond(200, list(self.server.users.values()))
        elif path.startswith("/api/users/"):
            user = self.server.users.get(path.removeprefix("/api/users/"))
            self.respond(200, user) if user else self.respond(404, {"error": "User not found"})
        elif path == "/api/private":
            if self.headers.get("Authorization") != "Bearer learning-token":
                self.respond(401, {"error": "Unauthorized"})
            else:
                self.respond(200, {"message": "Access granted"})
        else:
            self.respond(404, {"error": "Route not found"})

    def do_POST(self):
        if urlparse(self.path).path != "/api/users":
            self.respond(404, {"error": "Route not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(size))
        except (ValueError, UnicodeDecodeError):
            self.respond(400, {"error": "Invalid JSON"})
            return
        name = payload.get("name") if isinstance(payload, dict) else None
        if not isinstance(name, str) or not name.strip():
            self.respond(400, {"error": "Name is required"})
            return
        user_id = self.server.next_id
        self.server.next_id += 1
        user = {"id": user_id, "name": name.strip()}
        self.server.users[str(user_id)] = user
        self.respond(201, user)

    def do_DELETE(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/users/"):
            self.respond(404, {"error": "Route not found"})
            return
        user = self.server.users.pop(path.removeprefix("/api/users/"), None)
        if user is None:
            self.respond(404, {"error": "User not found"})
        else:
            self.send_response(204)  # 204 deliberately has no JSON body.
            self.end_headers()


@library(scope="SUITE", auto_keywords=False)
class MockService:
    def __init__(self):
        self.server = None
        self.thread = None

    @keyword
    def start_mock_service(self):
        """Start a background server and return its base URL."""
        if self.server is None:
            self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            self.reset_mock_data()
            self.thread = Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
        return f"http://127.0.0.1:{self.server.server_port}"

    @keyword
    def reset_mock_data(self):
        """Give every test the same starting data. Tests run sequentially."""
        self.server.users = {"1": {"id": 1, "name": "Ada"}}
        self.server.next_id = 2

    @keyword
    def stop_mock_service(self):
        """Release the socket even when an assertion failed."""
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=5)
            self.server = None

    @keyword
    def user_should_have_name(self, user: dict, expected_name: str):
        """A custom Python assertion: AssertionError makes the Robot step fail."""
        if user.get("name") != expected_name:
            raise AssertionError(f"Expected name {expected_name!r}, got {user!r}")
