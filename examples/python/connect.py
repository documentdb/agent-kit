import os
from pathlib import Path

from pymongo import MongoClient


def main():
    options = {
        "tls": True,
        "tlsAllowInvalidCertificates": os.environ.get("DOCUMENTDB_TLS_ALLOW_INVALID") == "true",
        "retryWrites": False,
        "serverSelectionTimeoutMS": 5000,
        "socketTimeoutMS": 10000,
    }
    uri = os.environ.get("MONGODB_URI")
    if uri:
        client = MongoClient(uri, **options)
    else:
        filename = Path(os.environ.get("DOCUMENTDB_CONFIG", Path(__file__).resolve().parents[2] / ".env"))
        values = dict(
            line.split("=", 1) for line in filename.read_text().splitlines()
            if line and not line.startswith("#") and "=" in line
        )
        if not values.get("DOCUMENTDB_USERNAME") or not values.get("DOCUMENTDB_PASSWORD"):
            raise ValueError("Missing database credentials")
        client = MongoClient(
            os.environ.get("DOCUMENTDB_HOST", "127.0.0.1"),
            int(os.environ.get("DOCUMENTDB_PORT", values.get("DOCUMENTDB_PORT", "10260"))),
            username=values["DOCUMENTDB_USERNAME"],
            password=values["DOCUMENTDB_PASSWORD"],
            authSource="admin",
            authMechanism="SCRAM-SHA-256",
            **options,
        )
    with client:
        client.admin.command("ping")
    print("Authenticated database ping passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Connection failed ({type(error).__name__}); check credentials, endpoint, and trusted TLS configuration.")
        raise SystemExit(1)
