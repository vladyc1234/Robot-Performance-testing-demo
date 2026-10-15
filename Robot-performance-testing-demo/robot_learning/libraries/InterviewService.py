"""Orders API for interview practice; fake tokens and in-memory storage only.

HTTP handlers run in worker threads. A lock makes checking an idempotency key
and creating its order one atomic operation. Polling uses monotonic elapsed
time to simulate a background job; there is no real payment processor here.
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from time import monotonic
from urllib.parse import parse_qs, urlparse

from robot.api.deco import keyword, library


class OrdersHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def reply(self, status, body, **headers):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def identity(self):
        # Tokens represent different users, not different authorization levels.
        owner = {"Bearer alice-token": "alice", "Bearer bob-token": "bob"}.get(
            self.headers.get("Authorization")
        )
        if owner is None:
            self.reply(401, {"error": "invalid_token"}, **{"WWW-Authenticate": "Bearer"})
        return owner

    def do_POST(self):
        owner = self.identity()
        if owner is None:
            return
        if urlparse(self.path).path != "/orders":
            self.reply(404, {"error": "not_found"})
            return
        if self.headers.get_content_type() != "application/json":
            self.reply(415, {"error": "json_required"})
            return
        try:
            payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        except (ValueError, UnicodeDecodeError):
            self.reply(400, {"error": "invalid_json"})
            return
        # bool is a subclass of int in Python; exact type checking rejects true.
        if (not isinstance(payload, dict) or set(payload) != {"sku", "quantity"}
                or payload.get("sku") != "BOOK"
                or type(payload.get("quantity")) is not int
                or not 1 <= payload["quantity"] <= 5):
            self.reply(422, {"error": "invalid_order"})
            return
        key = self.headers.get("Idempotency-Key")
        if not key or not key.strip():
            self.reply(400, {"error": "idempotency_key_required"})
            return
        with self.server.lock:
            previous = self.server.keys.get((owner, key))
            if previous:
                old_payload, order_id = previous
                if payload != old_payload:
                    self.reply(409, {"error": "idempotency_conflict"})
                else:
                    self.reply(200, self.server.orders[order_id], **{"Idempotency-Replayed": "true"})
                return
            order_id = str(len(self.server.orders) + 1)
            order = {"id": order_id, "owner": owner, **payload, "status": "pending"}
            self.server.orders[order_id] = order
            self.server.keys[(owner, key)] = (payload, order_id)
            self.server.ready_at[order_id] = monotonic() + 0.4
            self.reply(201, order, Location=f"/orders/{order_id}")

    def do_GET(self):
        owner = self.identity()
        if owner is None:
            return
        parsed = urlparse(self.path)
        with self.server.lock:
            if parsed.path == "/orders":
                query = parse_qs(parsed.query, keep_blank_values=True)
                try:
                    page = int(query.get("page", ["1"])[0])
                    size = int(query.get("size", ["2"])[0])
                    if page < 1 or not 1 <= size <= 3:
                        raise ValueError
                except ValueError:
                    self.reply(400, {"error": "invalid_pagination"})
                    return
                rows = [order for order in self.server.orders.values() if order["owner"] == owner]
                start = (page - 1) * size
                self.reply(200, {"items": rows[start:start + size], "total": len(rows),
                                 "page": page, "size": size})
            elif parsed.path.startswith("/orders/"):
                order = self.server.orders.get(parsed.path.removeprefix("/orders/"))
                if order is None:
                    self.reply(404, {"error": "not_found"})
                elif order["owner"] != owner:
                    self.reply(403, {"error": "forbidden"})
                else:
                    if monotonic() >= self.server.ready_at[order["id"]]:
                        order["status"] = "confirmed"
                    self.reply(200, order)
            else:
                self.reply(404, {"error": "not_found"})


@library(scope="SUITE", auto_keywords=False)
class InterviewService:
    def __init__(self):
        self.server = None

    @keyword
    def start_interview_service(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), OrdersHandler)
        self.server.lock = Lock()
        self.reset_interview_data()
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return f"http://127.0.0.1:{self.server.server_port}"

    @keyword
    def reset_interview_data(self):
        with self.server.lock:
            self.server.orders = {}
            self.server.keys = {}
            self.server.ready_at = {}

    @keyword
    def stop_interview_service(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=5)
            self.server = None

    @keyword
    def order_should_match_contract(self, order: dict):
        """Focused contract assertion; this is not a full JSON Schema validator."""
        required = {"id", "owner", "sku", "quantity", "status"}
        if not required <= order.keys():
            raise AssertionError(f"Missing fields: {required - order.keys()}")
        for field in ("id", "owner", "sku", "status"):
            if not isinstance(order[field], str) or not order[field]:
                raise AssertionError(f"{field} must be a nonempty string")
        if type(order["quantity"]) is not int or not 1 <= order["quantity"] <= 5:
            raise AssertionError("quantity must be an integer between 1 and 5")
        if order["status"] not in {"pending", "confirmed"}:
            raise AssertionError(f"Unexpected status: {order['status']}")
