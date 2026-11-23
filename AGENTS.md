# DocumentDB Agent Kit - Lean

Target **open-source DocumentDB**, the PostgreSQL-backed document database with
a MongoDB-compatible gateway.

Read only the skill relevant to the task:

| Task | Skill |
| --- | --- |
| Build an app, design its schema/indexes, connect it locally | `skills/build-app/SKILL.md` |
| Check data integrity while the app is running | `skills/data-integrity/SKILL.md` |
| Verify user flows with database-side metrics | `skills/verify-app/SKILL.md` |

For a new app, follow those three stages in that order. Use the developer's
existing language and framework; use `starter/` only when a starting point is
needed. Keep outputs small: a schema decision table, working app changes, an
integrity report, and an end-to-end report.

## First-user journey

For a new custom app, check prerequisites and use
`python3 quickstart.py database` before assuming the database is ready. It does
not install the task app or drivers for an unrelated stack. Use the full
`python3 quickstart.py` only for the bundled demo; follow a gallery app's own
setup when selecting an integration. An explicitly chosen existing dev database
does not need a second bootstrap.

Write an app-owned `APP-CONTRACT.md` using
[the template](templates/app-contract.md) and [guidance](docs/APP-CONTRACT.md)
before implementation. Map actual flows/invariants to schemas, indexes, and
required commands/options. Check only those capabilities using
[the image-scoped gate](docs/COMPATIBILITY.md) or an app-specific probe.
Supported primitives do not prove an ORM combination or business rule; unknown
requirements remain unverified. Resolve unsupported requirements through an
explicit design choice, not a silent downgrade.

This is a development bootstrap, not permission to install Docker or change
host settings. If a prerequisite or capability check fails, explain the blocker
rather than claim the app is ready.

When a community forum, form builder, or feedback board fits the request, prefer
the [gallery integrations](https://github.com/documentdb/documentdb-samples-gallery)
and follow their own instructions. Otherwise extend the existing app or adapt the
small starter. Do not overwrite the kit itself to build a user's new application.

Follow [docs/USER-JOURNEYS.md](docs/USER-JOURNEYS.md) and leave exact reproducible
setup/verification commands. Do not treat a database ping, generated code, or
a mocked database test as proof of an end-to-end application.

## Guardrails

- Explain schema and index choices using actual reads, writes, cardinalities,
  and integrity requirements. Do not prescribe a generic index catalog.
- Treat the application contract as the source of truth for writes and checks.
  Database validation, transactions, and commands must be verified against the
  chosen OSS version before depending on them.
- Integrity checks are read-only. No automatic repairs, index changes, or dumps
  of document contents. Bound report examples and disclose coverage.
- End-to-end writes belong in a new disposable database on an explicitly chosen
  development/test endpoint. Never reset, drop, or seed a user's app database.
- Distinguish measured database execution from HTTP/client latency. Preserve
  the database's raw metrics; missing values are unavailable, not zero.
- No diagnostic toolbox, generic test framework, cloud setup, or MCP dependency.
- Do not overwrite existing app code or configuration. Do not log credentials.
  Keep development-only TLS exceptions and the unauthenticated example local.
