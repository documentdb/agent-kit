import argparse
import json
import time
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from bson import ObjectId, json_util

from app import make_server
from db import connect, initialize, list_command, new_task
from integrity import check_integrity


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def explain_query(database, command):
    raw = database.command({"explain": command, "verbosity": "executionStats"})
    stats = raw.get("executionStats", {})
    summary = {
        "nReturned": stats.get("nReturned"),
        "executionTimeMillis": stats.get("executionTimeMillis"),
        "totalDocsExamined": stats.get("totalDocsExamined"),
        "totalKeysExamined": stats.get("totalKeysExamined"),
        "explainCommandExecTimeMillis": raw.get("explainCommandExecTimeMillis"),
        "winningPlan": raw.get("queryPlanner", {}).get("winningPlan"),
    }
    return {"command": command, "summary": summary, "raw": raw}


def run():
    database_name = "lean_e2e_" + uuid4().hex
    report = {
        "ok": False,
        "databaseName": database_name,
        "checks": [],
        "http": [],
        "database": {},
        "failures": [],
    }
    client = server = thread = None

    def expect(condition, label):
        if not condition:
            raise AssertionError(label)
        report["checks"].append(label)

    try:
        client, database = connect(database_name)
        initialize(database)
        report["database"]["before"] = database.command({"collStats": "tasks", "scale": 1})
        server = make_server(database, port=0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"

        def request(method, path, body=None, status=200):
            start = time.perf_counter()
            req = Request(
                base_url + path,
                data=None if body is None else json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
                method=method,
            )
            try:
                response = urlopen(req, timeout=15)
            except HTTPError as error:
                response = error
            with response:
                actual_status = response.status
                content = json.loads(response.read())
            report["http"].append({
                "method": method,
                "path": path,
                "status": actual_status,
                "roundTripMillis": round((time.perf_counter() - start) * 1000, 3),
            })
            expect(actual_status == status, f"{method} {path}: HTTP {status}")
            return content

        request("GET", "/")
        request("GET", "/health")
        request("GET", "/tasks")
        first = request("POST", "/tasks", {"title": "Build the app", "labels": ["demo"]}, 201)
        first_id = ObjectId(first["_id"])
        key = {"_id": first_id}
        expect(first["status"] == "open", "create supplies open status")
        expect(database.tasks.find_one(key)["title"] == first["title"], "create persists to database")
        expect(request("GET", "/tasks/" + first["_id"]) == first, "detail matches persisted create")
        second = request("POST", "/tasks", {"title": "Ship the app", "status": "done"}, 201)
        listed = request("GET", "/tasks")
        expect(len(listed) == 2 and listed[0]["_id"] == second["_id"], "list sorts newest first")
        filtered = request("GET", "/tasks?status=open")
        expect([task["_id"] for task in filtered] == [first["_id"]], "list filters status")

        bad_inputs = [
            {},
            {"title": " "},
            {"title": "x" * 201},
            {"title": "bad", "status": {"$ne": "open"}},
            {"title": "bad", "labels": ["duplicate", "duplicate"]},
            {"title": "bad", "labels": ["x"] * 11},
            {"title": "bad", "labels": [7]},
            {"title": "bad", "labels": ["x" * 41]},
            {"title": "bad", "schemaVersion": 2},
            [],
        ]
        for payload in bad_inputs:
            request("POST", "/tasks", payload, 400)
        request("PATCH", "/tasks/" + first["_id"], {"createdAt": "client time"}, 400)
        request("PATCH", "/tasks/" + first["_id"], {"status": "invalid"}, 400)
        request("PATCH", "/tasks/" + first["_id"], {}, 400)
        request("GET", "/tasks?status=invalid", status=400)
        request("GET", "/tasks?status=open&status=done", status=400)
        request("GET", "/tasks/not-an-id", status=400)
        missing = str(ObjectId())
        request("GET", "/tasks/" + missing, status=404)
        request("PATCH", "/tasks/" + missing, {"status": "done"}, 404)
        request("DELETE", "/tasks/" + missing, status=404)
        expect(database.tasks.count_documents({}) == 2, "invalid writes do not add records")
        expect(database.tasks.find_one(key)["status"] == "open", "rejected patches do not persist")

        report["integrity"] = check_integrity(database)
        expect(report["integrity"]["ok"] and report["integrity"]["checked"] == 2, "valid data passes integrity")
        limited = check_integrity(database, max_documents=1)
        expect(not limited["ok"] and limited["coverage"] == "document_limited", "limited scan is not a global pass")
        bad = new_task({"title": "Out-of-band invalid fixture"})
        bad.update({"status": "invalid", "schemaVersion": True, "updatedAt": "not a BSON date"})
        database.tasks.insert_one(bad)
        stored_bad = database.tasks.find_one({"_id": bad["_id"]})
        invalid = check_integrity(database)
        expect(
            invalid["invalid"] == 1
            and {"status.value", "schemaVersion.value", "updatedAt.type"} <= set(invalid["violations"]),
            "integrity detects invalid out-of-band data",
        )
        expect(
            database.tasks.count_documents({}) == 3
            and database.tasks.find_one({"_id": bad["_id"]}) == stored_bad,
            "integrity does not modify data",
        )
        database.tasks.delete_one({"_id": bad["_id"]})

        queries = report["database"]["queries"] = {}
        for name, command in {
            "list": list_command(),
            "open_list": list_command("open"),
            "detail": {"find": "tasks", "filter": key, "limit": 1},
        }.items():
            queries[name] = explain_query(database, command)
            summary = queries[name]["summary"]
            expect(numeric(summary["nReturned"]), f"{name}: database returned count available")
            expect(
                numeric(summary["executionTimeMillis"])
                or numeric(summary["explainCommandExecTimeMillis"]),
                f"{name}: database execution time available",
            )
            expect(isinstance(summary["winningPlan"], dict), f"{name}: database winning plan available")

        patched = request("PATCH", "/tasks/" + first["_id"], {"title": "App built", "status": "done", "labels": []})
        expect(
            patched["title"] == "App built" and patched["status"] == "done" and patched["labels"] == []
            and patched["createdAt"] == first["createdAt"],
            "patch updates mutable fields and preserves creation time",
        )
        expect(database.tasks.find_one(key)["status"] == "done", "patch persists to database")
        expect(request("GET", "/tasks/" + first["_id"]) == patched, "patched data reads back through HTTP")
        expect(request("GET", "/tasks?status=open") == [], "status update changes filtered list")
        report["database"]["after"] = database.command({"collStats": "tasks", "scale": 1})
        for phase in ("before", "after"):
            stats = report["database"][phase]
            expect(
                all(numeric(stats.get(field)) for field in ("count", "size", "storageSize", "totalIndexSize")),
                f"{phase}: database count and size metrics available",
            )
        expect(report["database"]["after"]["count"] == 2, "database metrics reflect persisted fixtures")
        request("DELETE", "/tasks/" + first["_id"])
        request("GET", "/tasks/" + first["_id"], status=404)
        expect(database.tasks.find_one(key) is None, "delete persists to database")
        request("DELETE", "/tasks/" + second["_id"])
        expect(request("GET", "/tasks") == [], "all owned fixtures deleted")
        bounded_fixtures = [new_task({"title": f"Bounded list {i}"}) for i in range(101)]
        database.tasks.insert_many(bounded_fixtures)
        expect(len(request("GET", "/tasks")) == 100, "HTTP list is capped at 100 records")
        batched = check_integrity(database)
        expect(batched["ok"] and batched["checked"] == 101, "integrity scans across cursor batches")
        report["ok"] = True
    except AssertionError as error:
        report["failures"].append(str(error))
    except Exception as error:
        report["failures"].append(f"Execution failed: {type(error).__name__}")
    finally:
        if server is not None:
            try:
                if thread is not None and thread.is_alive():
                    server.shutdown()
                    thread.join(timeout=15)
                    if thread.is_alive():
                        raise RuntimeError("App thread did not stop")
                server.server_close()
            except Exception as error:
                report["failures"].append(f"App cleanup failed: {type(error).__name__}")
        if client is not None:
            try:
                client.drop_database(database_name)
            except Exception as error:
                report["failures"].append(f"Database cleanup failed: {type(error).__name__}")
            finally:
                client.close()
        report["ok"] = report["ok"] and not report["failures"]
    return report


def main():
    parser = argparse.ArgumentParser(description="Real HTTP + OSS DocumentDB smoke verification")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run()
    content = json_util.dumps(report, indent=2)
    print(content)
    if args.output:
        args.output.write_text(content + "\n")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
