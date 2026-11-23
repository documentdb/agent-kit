---
name: lean-documentdb-build-app
description: Build an application quickly with open-source DocumentDB. Design collections and indexes with explicit reasons, implement validated writes and bounded reads, and run the app locally. Use for new apps, adding DocumentDB to an existing app, or schema design.
---

# Build an app with OSS DocumentDB

Deliver a running app, not just database advice.

1. Identify the main user flows, existing stack, expected cardinalities, and
   critical invariants. Ask only for details that materially change the design.
   For a new custom app, check Docker/Compose and Python prerequisites, then run
   `python3 quickstart.py database` from the kit root. This does not select a
   framework or install the task app/PyMongo. Reuse an explicitly chosen existing
   dev database rather than starting another. Do not install host tools without
   permission or claim readiness after a failed gate. For the bundled demo only,
   use the full `python3 quickstart.py` and [task starter](../../starter/README.md).
   For forums, forms, or feedback portals, prefer a matching
   [real gallery integration](https://github.com/documentdb/documentdb-samples-gallery).
2. Fill the [app-owned contract](../../templates/app-contract.md) in the
   application's directory as `APP-CONTRACT.md` **before implementation**:
   collection, example document and BSON types, read/write pattern, embed versus
   reference choice, growth bound, invariant, index, and reason/tradeoff.
   See [the worked schema](../../starter/SCHEMA.md). Embed bounded data read and
   updated together; reference independently growing entities. Explain how
   references and denormalized values stay consistent if introduced. Use
   [the requirements-to-schema guide](../../docs/APP-CONTRACT.md).
3. Define one app-owned contract used by both writes and integrity checks:
   required fields, types, lengths, enums, schema version, timestamps, and
   business invariants. Include authorization/tenant rules when relevant.
   Do not assume MongoDB validators or multi-document transactions work on the
   selected OSS release. Map only the required commands/options to
   [capability probes](../../docs/COMPATIBILITY.md), for example
   `python3 quickstart.py compatibility --features crud,unique-index`.
   Record image, scope, and supported/unsupported/unverified evidence in the
   contract. A primitive pass does not prove the actual ORM/query combination.
   For unknown features, collect app-specific evidence; for unsupported ones,
   ask for the design choice before changing behavior.
4. Implement the smallest vertical slice: environment-driven connection,
   reusable client with timeouts, idempotent collection/index setup, validated
   inputs, one complete CRUD flow, bounded reads, and graceful error handling.
   Use server-generated IDs/timestamps and atomic single-document updates where
   possible. Never pass arbitrary client objects straight into database filters
   or updates. Handle missing IDs and invalid requests explicitly.
5. Start local OSS DocumentDB plus the app. Verify readiness through a real
   database ping. Explain local TLS exceptions; do not make them production
   defaults. Reuse an existing dev database only when explicitly chosen.
6. Hand off to the integrity and verification skills. Report how to start the
   app, the schema rationale, and the exact verified user flow.

Do not add a framework, cloud provisioning, a broad compatibility catalog,
or speculative abstractions. Extend the developer's app rather than force the
starter's Python stack. Index actual query shapes; a tiny fixture may correctly
use a collection scan, so do not promise index use without measurement.
