---
name: lean-documentdb-data-integrity
description: Check persisted application data against its schema and business invariants while an OSS DocumentDB app is running. Produce a read-only, coverage-aware report without diagnosis or automatic repair.
---

# Check the running app's data

1. Confirm the application database and collection scope. Read its schema
   [app-owned contract](../../docs/APP-CONTRACT.md) and existing validation code;
   reuse its invariant predicates rather than invent a second schema. The
   Markdown contract documents enforcement; it is not a universal validator.
2. Check required fields, BSON types, enums, bounds, schema versions, and
   business invariants. For references, check missing parents; for denormalized
   fields, check agreement with the source; for tenant data, check ownership
   consistency. Include only invariants that the app actually defines.
3. Use read-only, batched cursors or read-only aggregation, with an explicit
   time budget and bounded ID-only examples. Never load the whole dataset in
   memory or expose document bodies. Full scans can cost resources: agree on
   scope/budget before scanning a large or production dataset.
4. Report start/end time, database/collections, records checked, invalid records,
   violations per rule, example IDs, and whether coverage was complete,
   limited, or interrupted. A bounded sample is **not** a global integrity pass.
   Under concurrent writes the report is an observation, not a consistent
   multi-collection snapshot or a guarantee of future integrity.
5. Exit nonzero for violations or incomplete coverage; distinguish an execution
   error from a clean result. Recommend a separate, reviewed repair only if
   requested. Do not change data or indexes.

The [starter checker](../../starter/integrity.py) checks the task app's contract,
not arbitrary databases. Run it after the app starts:

```bash
docker compose exec app python integrity.py
docker compose exec app python integrity.py --max-documents 1000 --max-seconds 30
```

Adapt its `task_errors` rules and collection traversal together when changing
the app. Database constraints, if supported, complement this check but do not
replace application-specific integrity rules.
