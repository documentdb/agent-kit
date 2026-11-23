import argparse
import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path

from pymongo.errors import PyMongoError

from db import connect, task_errors


def check_integrity(database, max_documents=None, max_seconds=60):
    if max_documents is not None and max_documents <= 0:
        raise ValueError("max_documents must be positive")
    if not math.isfinite(max_seconds) or max_seconds <= 0:
        raise ValueError("max_seconds must be positive")
    report = {
        "database": database.name,
        "collection": "tasks",
        "startedAt": datetime.now(UTC).isoformat(),
        "checked": 0,
        "invalid": 0,
        "coverage": "complete",
        "maxDocuments": max_documents,
        "maxSeconds": max_seconds,
        "violations": {},
    }
    deadline = time.monotonic() + max_seconds
    cursor = database.tasks.find({}).batch_size(100).max_time_ms(int(max_seconds * 1000))
    try:
        with cursor:
            for task in cursor:
                if time.monotonic() >= deadline:
                    report["coverage"] = "time_limited"
                    break
                if max_documents is not None and report["checked"] >= max_documents:
                    report["coverage"] = "document_limited"
                    break
                report["checked"] += 1
                errors = task_errors(task)
                if errors:
                    report["invalid"] += 1
                for error in errors:
                    rule = report["violations"].setdefault(error, {"count": 0, "exampleIds": []})
                    rule["count"] += 1
                    if len(rule["exampleIds"]) < 5:
                        rule["exampleIds"].append(str(task["_id"])[:120])
    except PyMongoError as error:
        report["coverage"] = "interrupted"
        report["errorType"] = type(error).__name__
    report["finishedAt"] = datetime.now(UTC).isoformat()
    report["ok"] = report["invalid"] == 0 and report["coverage"] == "complete"
    return report


def main():
    parser = argparse.ArgumentParser(description="Read-only task data integrity check")
    parser.add_argument("--max-documents", type=int)
    parser.add_argument("--max-seconds", type=float, default=60)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    client = None
    try:
        client, database = connect()
        report = check_integrity(database, args.max_documents, args.max_seconds)
        result = 2 if "errorType" in report else (0 if report["ok"] else 1)
    except Exception as error:
        report = {"ok": False, "coverage": "interrupted", "errorType": type(error).__name__}
        result = 2
    finally:
        if client is not None:
            client.close()
    content = json.dumps(report, indent=2)
    print(content)
    if args.output:
        args.output.write_text(content + "\n")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
