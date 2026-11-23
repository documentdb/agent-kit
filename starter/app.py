import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import PyMongoError

from db import LIST_LIMIT, LIST_SORT, connect, initialize, new_task, public_task


def make_server(database, host="127.0.0.1", port=8000):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *_):
            pass

        def respond(self, status, body):
            content = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def body(self):
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16384:
                raise ValueError("Body must contain 1-16384 bytes")
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Use Content-Type: application/json")
            return json.loads(self.rfile.read(length))

        def dispatch(self):
            route = urlsplit(self.path)
            if route.path == "/" and self.command == "GET":
                return self.respond(200, {
                    "application": "documentdb-agent-kit-lean",
                    "message": "OSS DocumentDB task API is running. Start with GET /tasks or POST /tasks.",
                    "endpoints": ["/health", "/tasks", "/tasks/{id}"],
                })
            if route.path == "/health" and self.command == "GET":
                database.command("ping")
                return self.respond(200, {"ok": True})
            if route.path == "/tasks":
                if self.command == "POST":
                    task = new_task(self.body())
                    database.tasks.insert_one(task)
                    # Read back BSON's stored millisecond-precision timestamps.
                    return self.respond(201, public_task(database.tasks.find_one({"_id": task["_id"]})))
                if self.command == "GET":
                    query = parse_qs(route.query, keep_blank_values=True)
                    if set(query) - {"status"} or any(len(v) != 1 for v in query.values()):
                        raise ValueError("Only one optional status parameter is supported")
                    status = query.get("status", [None])[0]
                    if status is not None and status not in ("open", "done"):
                        raise ValueError("status must be open or done")
                    tasks = database.tasks.find(
                        {} if status is None else {"status": status}
                    ).sort(LIST_SORT).limit(LIST_LIMIT)
                    with tasks:
                        return self.respond(200, [public_task(task) for task in tasks])
                return self.respond(405, {"error": "Method not allowed"})
            parts = route.path.split("/")
            if len(parts) != 3 or parts[1] != "tasks":
                return self.respond(404, {"error": "Not found"})
            if not ObjectId.is_valid(parts[2]):
                raise ValueError("Invalid task ID")
            key = {"_id": ObjectId(parts[2])}
            if self.command == "GET":
                task = database.tasks.find_one(key)
            elif self.command == "PATCH":
                payload = self.body()
                if not isinstance(payload, dict) or not payload:
                    raise ValueError("Patch must be a nonempty object")
                validated = new_task({"title": "placeholder", **payload})
                changes = {field: validated[field] for field in payload}
                changes["updatedAt"] = validated["updatedAt"]
                task = database.tasks.find_one_and_update(
                    key, {"$set": changes}, return_document=ReturnDocument.AFTER
                )
            elif self.command == "DELETE":
                if not database.tasks.delete_one(key).deleted_count:
                    return self.respond(404, {"error": "Task not found"})
                return self.respond(200, {"deleted": True})
            else:
                return self.respond(405, {"error": "Method not allowed"})
            if task is None:
                return self.respond(404, {"error": "Task not found"})
            return self.respond(200, public_task(task))

        def handle_request(self):
            try:
                self.dispatch()
            except (ValueError, UnicodeDecodeError) as error:
                self.respond(400, {"error": str(error)})
            except PyMongoError:
                self.respond(503, {"error": "Database operation failed"})

        do_GET = handle_request
        do_POST = handle_request
        do_PATCH = handle_request
        do_DELETE = handle_request

    return ThreadingHTTPServer((host, port), Handler)


def main():
    client = None
    try:
        client, database = connect()
        initialize(database)
        with make_server(
            database,
            os.environ.get("APP_HOST", "127.0.0.1"),
            int(os.environ.get("APP_PORT", "8000")),
        ) as server:
            print(f"Task API listening on port {server.server_port}", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    except (PyMongoError, ValueError, OSError):
        print("App startup failed; check database connection and configuration.", flush=True)
        return 2
    finally:
        if client is not None:
            client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
