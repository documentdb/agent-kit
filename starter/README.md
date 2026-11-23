# Runnable task starter

Use `python3 quickstart.py` from the kit root; see the
[root quickstart](../README.md). It prepares verified wheel files and private
configuration before building this Docker stack. PyMongo and its pinned
dnspython dependency are installed; HTTP serving, validation, integrity checks,
and the end-to-end flow use the standard library. No MongoDB shell or PostgreSQL
admin credentials.

## Configuration

| Environment variable | Default / meaning |
| --- | --- |
| `MONGODB_URI` | Optional full URI; overrides host/credentials/TLS settings below. Never printed. |
| `DOCUMENTDB_HOST`, `DOCUMENTDB_PORT` | `127.0.0.1`, `10260` for host-side runs |
| `DOCUMENTDB_USERNAME`, `DOCUMENTDB_PASSWORD` | Required unless a URI is supplied; passed as driver arguments, so special characters are safe |
| `DOCUMENTDB_TLS_ALLOW_INVALID` | `false`; Compose explicitly enables it for its local self-signed certificate only |
| `DOCUMENTDB_DATABASE` | `lean_app`; checker and app use the same database |
| `APP_HOST`, `APP_PORT` | `127.0.0.1`, `8000`; Compose binds inside its container but publishes only on host loopback |
| `DOCUMENTDB_IMAGE` | Pinned OSS `documentdb-local` digest; overrides require fresh compatibility verification |

The client uses TLS, SCRAM-SHA-256, no retryable writes, a 5-second selection
timeout and 10-second socket timeout. Collection/index setup runs once at app
startup, is idempotent, and never drops or replaces existing data/indexes.
Keep the same generated credentials across stack restarts; the data volume
persists. Only point the unauthenticated API at development data.

To run Python directly against an already running local OSS gateway:

```bash
cd starter
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
# Export the gateway credentials or MONGODB_URI first.
export DOCUMENTDB_TLS_ALLOW_INVALID=true  # local self-signed gateway only
python app.py
# In another terminal with the same connection environment:
python integrity.py
python e2e.py --output e2e-report.json
```

`GET /health` pings the database. API errors use JSON and do not reveal database
exceptions. Requests are capped at 16 KiB, use an object body, reject unknown
fields, and validate IDs, titles, statuses, and bounded labels.

## Integrity report

```bash
python integrity.py --max-documents 10000 --max-seconds 60 --output integrity-report.json
```

Without `--max-documents`, scans all tasks subject to the time budget (default
60 seconds). Cursor batches bound memory; at most five IDs per rule are shown.
Exit status: **0** = clean complete observation, **1** = violations or incomplete
coverage, **2** = execution/configuration error. On concurrent writes this is not
a point-in-time snapshot. An empty collection is reported as zero checked,
not proof of write-path coverage.

## End-to-end report

`python e2e.py` requires no prestarted API: it starts the real `app.py` against a
new `lean_e2e_<random>` database on the configured **dev/test endpoint**, using
the same HTTP handler and database setup in a background server thread. The app
database setting is deliberately ignored. That server and only that disposable
database are cleaned up in `finally`, including on failed checks.

The flow covers HTTP create/detail/filtered and unfiltered list/update/delete,
invalid inputs and unknown IDs, direct persisted read-back, valid integrity,
and detection of an invalid out-of-band write without changing it.

| Report field | Interpretation |
| --- | --- |
| `http` | Measured round-trip milliseconds for each request; includes app, network, driver, and database work |
| `database.before` / `database.after` | Raw `collStats` responses, `scale: 1` (bytes), captured around the CRUD flow while a task exists |
| `database.queries` | Raw `executionStats` explains for the app's unfiltered list, filtered list, and ID lookup |
| `database.queries.*.summary` | Available server metrics and plan; absent fields are `null`, never made up |
| `integrity` | Read-only report of valid persisted fixtures |
| `checks` / `failures` | Functional assertions and any execution or cleanup error |

At least one numeric execution time, returned count, winning plan, and numeric
collection count/storage/index sizes must be returned or verification fails.
Examined counts are retained when available but differ by OSS release.
**Explain re-executes reads**; these metrics are not attributed to the earlier
HTTP requests. Storage deltas are not a per-request cost. There are no load,
throughput, p95, CPU, or production-readiness claims.

The Docker image and driver versions are pinned. Record any override when
comparing results. The app and scripts do not dump user document contents or
connection strings into reports.
