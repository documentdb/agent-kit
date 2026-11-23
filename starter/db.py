import os
from datetime import UTC, datetime

from bson import ObjectId
from pymongo import MongoClient


LIST_SORT = [("createdAt", -1), ("_id", 1)]
LIST_LIMIT = 100
FIELDS = {"_id", "schemaVersion", "title", "status", "labels", "createdAt", "updatedAt"}
MUTABLE_FIELDS = {"title", "status", "labels"}


def connect(database_name=None):
    options = {
        "appname": "documentdb-agent-kit-lean",
        "retryWrites": False,
        "tz_aware": True,
        "serverSelectionTimeoutMS": 5000,
        "connectTimeoutMS": 5000,
        "socketTimeoutMS": 10000,
    }
    uri = os.environ.get("MONGODB_URI")
    if uri:
        client = MongoClient(uri, **options)
    else:
        username = os.environ.get("DOCUMENTDB_USERNAME")
        password = os.environ.get("DOCUMENTDB_PASSWORD")
        if not username or not password:
            raise ValueError("Set DOCUMENTDB_USERNAME/PASSWORD or MONGODB_URI")
        client = MongoClient(
            os.environ.get("DOCUMENTDB_HOST", "127.0.0.1"),
            int(os.environ.get("DOCUMENTDB_PORT", "10260")),
            username=username,
            password=password,
            authSource="admin",
            authMechanism="SCRAM-SHA-256",
            tls=True,
            tlsAllowInvalidCertificates=(
                os.environ.get("DOCUMENTDB_TLS_ALLOW_INVALID", "false").lower() == "true"
            ),
            **options,
        )
    database = client[database_name or os.environ.get("DOCUMENTDB_DATABASE", "lean_app")]
    try:
        client.admin.command("ping")
    except Exception:
        client.close()
        raise
    return client, database


def initialize(database):
    if "tasks" not in database.list_collection_names():
        database.create_collection("tasks")
    database.tasks.create_index(
        [("status", 1), *LIST_SORT], name="status_created_id"
    )
    database.tasks.create_index(LIST_SORT, name="created_id")


def task_errors(task):
    errors = []
    if set(task) - FIELDS:
        errors.append("unknown_fields")
    for field in sorted(FIELDS - set(task)):
        errors.append(f"{field}.required")
    if not isinstance(task.get("_id"), ObjectId):
        errors.append("_id.type")
    if type(task.get("schemaVersion")) is not int or task["schemaVersion"] != 1:
        errors.append("schemaVersion.value")
    title = task.get("title")
    if not isinstance(title, str) or not 1 <= len(title) <= 200 or not title.strip():
        errors.append("title.value")
    if task.get("status") not in ("open", "done"):
        errors.append("status.value")
    labels = task.get("labels")
    if (
        not isinstance(labels, list)
        or len(labels) > 10
        or any(not isinstance(label, str) or not 1 <= len(label) <= 40
               or not label.strip() for label in labels)
    ):
        errors.append("labels.value")
    elif len(set(labels)) != len(labels):
        errors.append("labels.unique")
    valid_dates = True
    for field in ("createdAt", "updatedAt"):
        value = task.get(field)
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            errors.append(f"{field}.type")
            valid_dates = False
    if valid_dates and task["updatedAt"] < task["createdAt"]:
        errors.append("timestamps.order")
    return errors


def new_task(payload):
    if not isinstance(payload, dict) or set(payload) - MUTABLE_FIELDS:
        raise ValueError("Expected an object containing only title, status, labels")
    now = datetime.now(UTC)
    task = {
        "_id": ObjectId(),
        "schemaVersion": 1,
        "title": payload.get("title"),
        "status": payload.get("status", "open"),
        "labels": payload.get("labels", []),
        "createdAt": now,
        "updatedAt": now,
    }
    errors = task_errors(task)
    if errors:
        raise ValueError(", ".join(errors))
    return task


def list_command(status=None):
    return {
        "find": "tasks",
        "filter": {} if status is None else {"status": status},
        "sort": dict(LIST_SORT),
        "limit": LIST_LIMIT,
    }


def public_task(task):
    return {
        **task,
        "_id": str(task["_id"]),
        "createdAt": task["createdAt"].isoformat(),
        "updatedAt": task["updatedAt"].isoformat(),
    }
