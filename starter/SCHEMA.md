# Task app: schema and reasons

One collection, `tasks`, in database `lean_app`:

```javascript
{
  _id: ObjectId("..."),
  schemaVersion: 1,
  title: "Build with DocumentDB",
  status: "open",
  labels: ["demo"],
  createdAt: ISODate("2026-01-01T00:00:00Z"),
  updatedAt: ISODate("2026-01-01T00:00:00Z")
}
```

| Decision | Reason and tradeoff |
| --- | --- |
| One task per document | Detail reads and edits need the same small unit; each write is atomic without a cross-document transaction. |
| Embed up to 10 unique labels, each 1-40 characters | Labels are read with the task, have bounded growth, and have no independent lifecycle. No extra collection or lookup. Shared label metadata would justify references later. |
| Title: 1-200 characters, nonblank; status: `open`/`done` | Explicit application invariants keep the first API useful and its document size bounded. No free-form payload or unbounded history array. |
| Server-generated BSON ObjectId and UTC BSON dates | No client-provided keys or timestamps; creation time is immutable and update time must not precede it. API dates are ISO 8601 strings; storage dates remain BSON dates. |
| `schemaVersion: 1`, no unknown fields | Persisted data has a known shape. A future contract change needs an explicit migration and compatible checker, not silently reinterpreted old documents. |
| Existing unique `_id` index | Supports detail reads, updates, and deletes. No redundant ID index. |
| `status_created_id`: `{status: 1, createdAt: -1, _id: 1}` | Matches `GET /tasks?status=open` (equality plus newest-first sorting and deterministic tie-break). Do not claim the planner must use it on tiny datasets. |
| `created_id`: `{createdAt: -1, _id: 1}` | Matches the unfiltered list; the leading `status` in the other index does not match that sort. Two app indexes trade write/storage cost for the two shipped list flows. |
| Limit lists to 100 | Prevents an unbounded API response. This first version has no pagination, tenant model, history, or references. Add those only when the app needs them. |

`db.py:task_errors` is the contract, shared by API writes and `integrity.py`.
Creation supplies defaults; patches accept only mutable fields and validate
their values before using `$set`. The checker also finds malformed documents
inserted outside the API. This version does **not** install a database validator:
application validation is not a guarantee against other writers.

The integrity report covers fields, BSON types, bounds, versions, and timestamp
ordering. There are no reference or denormalized-value checks because this
schema defines neither. It never repairs documents.

## OSS references

Relevant surfaces in the OSS source (also inspected in the local checkout):

- [`README.md`](https://github.com/documentdb/documentdb/blob/main/README.md) describes the OSS image, gateway
  port 10260, TLS, and PyMongo connection.
- [`documentdb-local/examples/docker-compose/docker-compose.yml`](https://github.com/documentdb/documentdb/blob/main/documentdb-local/examples/docker-compose/docker-compose.yml)
  documents credential environment variables, persistence, and image health.
- [`pg_documentdb_gw/documentdb_gateway_core/src/explain/documentdb_explain_output.schema.json`](https://github.com/documentdb/documentdb/blob/main/pg_documentdb_gw/documentdb_gateway_core/src/explain/documentdb_explain_output.schema.json)
  describes the gateway's `queryPlanner`, `executionStats`, and explain timing
  fields. Releases may expose a different subset.
- [`pg_documentdb/src/commands/coll_stats.c`](https://github.com/documentdb/documentdb/blob/main/pg_documentdb/src/commands/coll_stats.c)
  emits collection count, data/storage size, and index size.

No sibling source checkout is needed to run this kit. No Azure cluster tiers,
SLAs, or managed-only APIs are assumed.
