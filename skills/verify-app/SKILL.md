---
name: lean-documentdb-verify-app
description: Verify real application user flows end to end against OSS DocumentDB and capture database execution and storage metrics separately from HTTP latency. Use for a runnable smoke check, not a generic test or diagnosis framework.
---

# Verify the app with database metrics

1. Select an explicit development/test endpoint. Use a new randomly named
   disposable database and the real app implementation. Never clear an existing
   database or run a destructive flow against live app data.
2. Drive user flows through HTTP/UI, not just direct database CRUD: create,
   read/list, update, persisted read-back, delete, missing records, and invalid
   inputs. Check the actual response values and that rejected writes did not
   persist. Add only business-specific flows the app needs.
3. Run the app's integrity check while the test app is alive. Confirm it detects
   a deliberately invalid fixture in the disposable database and remains
   read-only. Remove only the test's fixture.
4. Capture database-side metrics for representative **actual app query shapes**:
   `explain` with `executionStats`, and `collStats` before/after the user flow.
   Preserve raw responses. Report available returned/examined counts, execution
   time, winning plan, document count, data/storage bytes, and index bytes.
   OSS versions can differ; record missing fields as unavailable and fail if
   required evidence cannot be collected. Do not silently substitute client
   timings or manufactured zeros.
5. Label HTTP timings separately. An explain performs a separate query and
   may instrument it: it is not the timing of the earlier HTTP request.
   Collection size deltas are observations, not per-request resource usage.
   A small smoke flow says nothing about production throughput or p95 latency.
6. Always stop the owned app server and drop only the generated database, even
   on failure. Exit nonzero for assertion/metric/cleanup failures; produce a
   compact, machine-readable report with failures and the raw evidence.

The [starter flow](../../starter/e2e.py) uses Python's standard library and
PyMongo, no test framework:

```bash
docker compose exec app python e2e.py
docker compose exec app python e2e.py --output /tmp/e2e-report.json
```

For an existing app, retain its stack and existing testing tools. Implement a
small app-specific flow; do not introduce a general-purpose harness or a
diagnostic advisor.
