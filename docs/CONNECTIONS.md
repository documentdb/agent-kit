# Use the database with your own stack

```bash
python3 quickstart.py database
```

This starts and authenticates **only OSS DocumentDB** on the configured loopback
port. It uses the same private `.env`/data volume as the full starter, preserving
credentials across starts. It does not fetch Python driver wheels, build the task
app, install a Node driver, or choose your framework. If an app from an earlier
full start is already running, the database command leaves it untouched.

Use `--db-port 10261` for a conflict; use `python3 quickstart.py stop` to stop this
project while retaining data/config. Readiness is authenticated, not just a TCP
or TLS handshake. Docker/Compose and Python remain host prerequisites for this
small bootstrap; language-specific packages are optional and app-owned.

## Node.js example

Only if Node is your chosen stack: requires Node **20.19+** and npm. The example
pins the MongoDB driver; no Express/framework is installed.

```bash
npm install --prefix examples/node
DOCUMENTDB_TLS_ALLOW_INVALID=true npm start --prefix examples/node
```

[connect.cjs](../examples/node/connect.cjs) reads the kit's private `.env` without
a dotenv dependency and performs an authenticated read-only ping. It does not
print a URI or password. Copy/adapt it into your app, reusing your existing
configuration and one long-lived client rather than connecting per request.

## Python example

Only if Python is your chosen stack: install its driver in an app-owned virtual
environment. Do not install it globally just to start DocumentDB.

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r examples/python/requirements.txt
DOCUMENTDB_TLS_ALLOW_INVALID=true python3 examples/python/connect.py
```

[connect.py](../examples/python/connect.py) uses the same private configuration
and read-only ping. If your Python installation lacks venv/pip, install those
prerequisites through your normal environment setup only when choosing Python.

## Configuration and TLS

Both examples accept `MONGODB_URI` from your app's secret configuration instead
of reading the kit file. Never paste credentials into source or log the URI.
Without a URI, they read `DOCUMENTDB_CONFIG` (default: kit `.env`) and use the
generated username/password with SCRAM-SHA-256, admin authentication, TLS,
timeouts, and retryable writes disabled.

`DOCUMENTDB_HOST` / `DOCUMENTDB_PORT` can override the local endpoint; inside an
approved Compose network use its service hostname and internal port 10260,
not the published host port. Keep credentials out of Docker command arguments.

`DOCUMENTDB_TLS_ALLOW_INVALID=true` is an **explicit local-only** exception for
the pinned development image's self-signed certificate. The examples default
to certificate verification; trusted deployments should leave this flag unset
and use their approved CA/TLS configuration. A successful ping establishes
connection/authentication, not support for every app operation: follow
[the feature-scoped compatibility gate](COMPATIBILITY.md).
