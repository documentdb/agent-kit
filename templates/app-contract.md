# Application data contract

Copy into the application's own directory as `APP-CONTRACT.md`. Replace the
placeholders before implementation; do not modify the kit template.
This is a design/enforcement document, not a runtime schema engine or test format.

## Intent and environment

- Application and smallest useful user outcome: `<describe>`
- Existing language/framework/driver: `<versions; explain any new choice>`
- Intended development endpoint: `<no credentials>`
- DocumentDB configured image and resolved image ID: `<pin/evidence>`
- Expected scale and growth bounds: `<documents, relationships, payload sizes>`
- Open questions that materially change the schema: `<ask before coding>`

## User flows and query shapes

| Flow ID | Actor/tenant boundary | Read filter, sort, projection, limit | Write and concurrent-writer behavior |
| --- | --- | --- | --- |
| `<flow>` | `<who may access what>` | `<actual query shape>` | `<operation and condition; not just "CRUD">` |

## Collections and BSON documents

For each collection, include a representative document with actual BSON types,
required/optional fields, schema version, size/growth bounds, and relationships.
Use generated IDs/dates where appropriate; do not include real secrets or data.

```javascript
// Replace with this application's document shape and BSON types.
{ _id: ObjectId("..."), schemaVersion: 1, createdAt: ISODate("...") }
```

| Collection/relationship | Embed or reference? | Reason tied to flows and growth | Tradeoff/alternative rejected |
| --- | --- | --- | --- |
| `<name>` | `<bounded embedding or independent entity>` | `<reads/writes/cardinality/lifecycle>` | `<cost or consistency obligation>` |

## Invariants and enforcement

| Rule ID | Exact predicate | Enforcement owner/mechanism | Atomicity/consistency boundary | Read-only integrity observation |
| --- | --- | --- | --- | --- |
| `<rule>` | `<required fields, BSON types, bounds, enum, uniqueness, ownership, reference, transition>` | `<shared app validator, unique index, conditional update, permission guard>` | `<one document, cross-document obligation, or unresolved>` | `<app-native check, scoped/batched; bounded ID examples>` |

Specify creation defaults, immutable fields, permitted transitions, idempotency
keys, timestamp ordering, and missing-parent/deletion behavior when applicable.
Reuse app-owned validation rules in writes and checks; do not invent a second
independent schema. State what other writers can bypass.

## Index decisions

| Index key/options | Flow IDs served | Reason | Write/storage cost and limitations |
| --- | --- | --- | --- |
| `<exact shape/options>` | `<flows>` | `<equality/sort/range or invariant>` | `<tradeoff; do not promise index use on tiny fixtures>` |

Avoid indexes without a real query or invariant. List any special options
(unique, partial, multikey, TTL, collation) as compatibility requirements.

## Required capabilities and evidence

| Requirement | Why the app needs it | Built-in probe, if relevant | Result on selected image | Additional app-specific evidence needed |
| --- | --- | --- | --- | --- |
| `<exact command/options/semantics>` | `<flow/rule IDs>` | `<ID from docs/COMPATIBILITY.md or none>` | `<supported / unsupported / unverified, date and image ID>` | `<query shape, concurrency, combinations, expiry, ORM options>` |

Probe only required capabilities on a disposable development database. A
primitive probe is not evidence for every option combination or business rule.
Keep unverified requirements explicit; do not silently downgrade or replace them.
For unsupported requirements, obtain an explicit design choice before proceeding.

## Schema evolution and unresolved decisions

- Version/read compatibility and migration ownership: `<describe>`
- Rollout behavior while old and new app versions overlap: `<describe>`
- Reference/denormalized-data maintenance and deletion policy: `<describe>`
- Remaining compatibility/consistency questions and chosen alternative: `<describe>`
