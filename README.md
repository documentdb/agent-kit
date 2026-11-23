# DocumentDB Agent Kit

A lean, developer-first kit for building applications with **open-source
[DocumentDB](https://github.com/documentdb/documentdb)**: design the data,
build the app, check its integrity, and verify real user flows with database-side
metrics. This is a first version, not a production platform.

## What is included

| Capability | Agent guidance | Working example |
| --- | --- | --- |
| App building and schema design **with reasons** | [Build app](skills/build-app/SKILL.md) | Task HTTP API and [schema decisions](starter/SCHEMA.md) |
| Database-only setup for your own stack | [Connections](docs/CONNECTIONS.md) | `python3 quickstart.py database`; optional Node/Python examples |
| Requirements-to-schema contract | [App contract](docs/APP-CONTRACT.md) | [Copyable app-owned template](templates/app-contract.md) |
| Version-scoped capability checks | [Compatibility](docs/COMPATIBILITY.md) | Explicit required-feature probes; supported/unsupported/unverified |
| Integrity checks on a running app | [Data integrity](skills/data-integrity/SKILL.md) | Read-only, streaming check using the same contract as writes |
| End-to-end verification and database metrics | [Verify app](skills/verify-app/SKILL.md) | HTTP CRUD, invalid writes, persisted data, `explain`, and `collStats` |

There is no MCP dependency, diagnostic toolbox, benchmark harness, test
framework, or cloud provisioning. The starter uses Python's standard library
plus **PyMongo**. The skills are stack-independent; the task API is a small
example to adapt, not a required architecture.

## Build your own app without the starter

```bash
python3 quickstart.py database
python3 quickstart.py compatibility --features crud,unique-index,compound-index
```

This starts only the pinned database and checks authenticated readiness. It
does **not** download driver wheels, build the task app, or install Node/Python
packages. Credentials/data are reused; `--db-port` handles conflicts, and
`python3 quickstart.py stop` stops the owned stack without deleting its volume.
If the starter is already running, the database command leaves it untouched.

Use the [connection examples](docs/CONNECTIONS.md) for your chosen runtime.
Before implementing, fill the [app contract](docs/APP-CONTRACT.md) in your own
application directory: user flows, query shapes, BSON documents, invariants,
index reasons, and required capabilities. Probe only those requirements.
Results are qualified by the running image and probe scope; unknown requirements
stay **unverified**. This adds no universal validator or common app test/report
contract. See [compatibility limits and exit codes](docs/COMPATIBILITY.md).

## Start here: a working app, database, and verification

Install **Docker with Compose 2.20+** and **Python 3.9+** on your computer.
Start Docker, using Linux containers. You need registry/PyPI HTTPS access;
no host Node.js, pip, MongoDB, PostgreSQL, cloud account, or AI API key is needed.
Linux/macOS Docker Desktop and Windows WSL2 are the intended environments.

```bash
git clone https://github.com/documentdb/agent-kit.git
cd agent-kit
python3 quickstart.py
```

One command generates and preserves private credentials, downloads the pinned
OSS DocumentDB and Python images, verifies driver-package hashes, starts the
database/API, and runs real end-to-end and integrity checks. Driver wheels are
fetched using the host's trusted HTTPS configuration and installed offline
inside Docker; no insecure package-TLS workaround is required.

**Success means:** an API at `http://127.0.0.1:8000`, passing user-flow checks,
real database execution/storage metrics, and full evidence in
`.runtime/e2e-report.json` / `.runtime/integrity-report.json`.
Startup duration depends on image downloads and your computer, not an advertised
time promise. Do not proceed on a nonzero exit or claim success from a ping alone.

If a port is occupied, rerun
`python3 quickstart.py --app-port 8001 --db-port 10261`. This preserves credentials
and data. Re-running the normal command reuses your settings and re-verifies them.

The API is at `http://127.0.0.1:8000`. Try it:

```bash
curl -sS http://127.0.0.1:8000/tasks
curl -sS http://127.0.0.1:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"Build with DocumentDB","labels":["demo"]}'
curl -sS 'http://127.0.0.1:8000/tasks?status=open'
```

`POST /tasks`, `GET /tasks`, `GET /tasks/{id}`, `PATCH /tasks/{id}`, and
`DELETE /tasks/{id}` are supported. PATCH accepts `title`, `status`
(`open` or `done`), and `labels`. Lists return at most 100 tasks, newest first.

`e2e.py` prints a JSON report and exits nonzero on a failed assertion or missing
required database metrics. It starts a separate instance of the **same app** on
an ephemeral loopback port, with a unique database, then cleans up both. It is a
functional smoke check, not a load test. See [starter usage](starter/README.md)
for configuration, metric interpretation, and report files.

Recheck with `python3 quickstart.py verify`; run a read-only app-data check with
`python3 quickstart.py check`. Stop with `python3 quickstart.py stop`; the database
volume and private `.env` are retained. Do not regenerate that file while keeping
its data. The initial app collection is empty; the separate end-to-end database
proves the write path without seeding your app.

## Build your own app with an agent

Point your coding agent at [AGENTS.md](AGENTS.md), or install/copy the three
`skills/` directories into its supported skills location. No installer or
agent-specific plugin is required in v0.1.

Copy this prompt into your coding agent, replacing the application description:

```text
Read AGENTS.md and the build-app skill.
Build [my application] with OSS DocumentDB, using my existing stack.
If no stack exists, explain the smallest suitable choice.
For a new custom app, confirm prerequisites and run python3 quickstart.py database.
For the bundled demo only, use python3 quickstart.py.
Use a real gallery integration when appropriate rather than starting from scratch.
Explain schema/index choices against my user flows before implementation.
Write APP-CONTRACT.md in my application using the kit template.
Check only the required capabilities on the selected image; leave unknown ones
unverified and obtain evidence or a design decision before depending on them.
Reuse the app's contract for read-only integrity checks.
Verify actual user flows, persisted data, and database-side metrics on a new
disposable development database. Do not touch production or repair data.
Do not call the app finished until its setup and verification commands pass.
```

See [the two user journeys](docs/USER-JOURNEYS.md) for success gates, expected
artifacts, reruns, failure recovery, and the campaign publication checklist.

## Boundaries

The Compose stack is **local development only**: loopback ports, generated
credentials, and an explicit exception for the database's self-signed TLS
certificate. The demo HTTP API has no authentication or authorization. Before
deploying, add these, use trusted TLS, and review secrets, backup, migration,
and capacity requirements. The default database, runtime, and driver dependencies
are pinned; changing a pin requires rerunning the documented cold-start checks.

Only the MongoDB-compatible gateway is used; no PostgreSQL admin access is
required. Compatibility is checked against OSS, not inferred from MongoDB or
the managed Azure service. [Source references](starter/SCHEMA.md#oss-references)
document the features used.

The kit's original code and skills use the [MIT license](LICENSE).
Third-party dependencies retain their own licenses.
