# Check the features your app actually requires

DocumentDB exposes a MongoDB-compatible API, not a blanket guarantee that every
driver/ORM option works. Derive requirements from the
[app contract](APP-CONTRACT.md), then probe **only those requirements** on the
selected local image.

```bash
python3 quickstart.py database
python3 quickstart.py compatibility --features crud,unique-index,compound-index
```

The command uses the kit's own database container and its bundled `mongosh`;
it does not install PyMongo, Node packages, or the task app. It authenticates,
creates a random `lean_probe_...` database only for known write probes, performs
tiny scoped operations, and drops **only that database** in `finally`.
It never resets an app database, inspects production data, repairs data, or
changes a user's indexes.

No features are selected by default. IDs are case-sensitive; unknown IDs remain
unverified rather than being silently ignored or treated as unsupported.

## Included narrow probes

| ID | What is checked | What is not established |
| --- | --- | --- |
| `crud` | Insert, equality read, single-document `$set`/`$inc`, delete | Every operator, large payload, upsert variant, or concurrent business predicate |
| `unique-index` | Scalar unique index rejects a duplicate and leaves one record | Every partial, sparse, multikey, compound, or collation combination |
| `compound-index` | Compound index metadata plus equality filter/descending-sort results | Planner index selection or unique-compound semantics |
| `ttl-index-definition` | TTL index creation and `expireAfterSeconds` metadata | Background deletion timing or expiration-based authorization |
| `case-insensitive-collation` | Case-insensitive index creation and find comparison | Every locale/strength/operator |
| `multi-document-transactions` | Abort and commit across two collections through a session | Every isolation level, read/write concern, recovery case, or ORM transaction flow |

If you need TTL **expiration**, a search index, a specific aggregate, an empty-sort
ORM behavior, or another unlisted requirement, record it as unverified and run
an app-specific check. Do not add a broad conformance/diagnostic catalog to this
kit. The included primitives do not replace checks of the exact app query shape.

## Interpreting evidence

Output identifies the observation time, configured image reference, resolved
architecture-specific image ID, per-feature scope/result, and whether the
temporary database was removed. It also records the bundled shell version and
probe source hash. Keep it with the app's design evidence.
The image identity is the version boundary: a MongoDB-compatible `buildInfo`
version is not necessarily the DocumentDB engine version.

- **supported:** the documented probe behavior passed on that image/client.
- **unsupported:** a documented behavior failed or the server explicitly rejected
  that capability. This is a design blocker, not permission to silently patch an ORM.
- **unverified:** no probe exists, execution/readiness failed without decisive
  support evidence, or cleanup could not be confirmed. Stop treating it as proven.

Exit **0** means every requested feature passed; **1** means unsupported
requirements; **2** means unverified/error evidence (including mixed outcomes).
Read the full scope/status, not just the exit code or a database ping.

For an unsupported requirement, explain alternatives and their semantic costs:
for example, explicit normalized fields instead of collation, or a single-document
conditional update instead of an unverified cross-document transaction.
Obtain a design decision before changing behavior. Application-specific adapters,
patches, and framework configuration remain in the app/gallery.

This is a development capability gate, not a performance advisor, production
diagnostic, universal compatibility matrix, test framework, or common app
verification/report contract. Re-run required probes when the image/driver or
required query/options change; image overrides need a fresh approved dev setup.
