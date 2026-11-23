# From application requirements to a schema with reasons

Use [the app contract template](../templates/app-contract.md) in the **application
directory**, not in this kit. Fill it before coding. Keep it short enough to
review: actual user flows -> query shapes -> documents -> invariants -> indexes
-> required capabilities. It is app-owned Markdown, not a new configuration,
validator library, or common verification/report contract.

## What the agent must establish

Ask only questions that materially change the design: actors/tenant boundaries,
the main reads/writes, relationship growth, and consistency requirements.
Respect the existing stack. For each schema/index choice, explain the reason
and the cost of the alternative; "document databases are flexible" is not a reason.

Explicitly connect:

- Data accessed/updated together to bounded embedding.
- Independently growing entities to references and a maintenance/deletion policy.
- Duplicate requests to an idempotency/uniqueness rule.
- Concurrent writers to conditional atomic updates rather than read-modify-write.
- Cross-document invariants to verified transactions or an explicitly chosen
  alternative. Do not assume a MongoDB API means transactions are supported.
- Required fields/types/bounds/versions to the **same app-owned validation**
  used on writes and in a read-only integrity observation.
- Index keys/options to actual filters/sorts or an invariant, including write cost.

## Small worked example: one-time invite acceptance

Assume an already authenticated user accepts an invitation. The invitation
document is the authoritative acceptance record; this example does **not**
also create a user or a separate membership row in the same operation.

```javascript
{
  _id: ObjectId("..."),
  schemaVersion: 1,
  tenantId: "team_123",
  tokenHash: "...",          // never store the raw invitation token
  expiresAt: ISODate("..."),
  redeemedAt: null,
  redeemedBy: null
}
```

| Decision | Reason |
| --- | --- |
| One invite per document | Expiry and redemption are read/updated as one bounded unit. No growing accepted-user array. |
| Unique `(tenantId, tokenHash)` | Retries cannot create the same invitation within a tenant; the compound shape also matches lookup. |
| Conditional redemption update | Filter on tenant, token hash, `redeemedAt: null`, and `expiresAt > now`; set redemption fields atomically and require exactly one match. Two successful lookups alone do not prevent double redemption. |
| No reliance on TTL timing | Expiry is enforced in the write predicate. TTL may clean up old records, but asynchronous deletion is not authorization. |
| Explicit user/reference policy | Auth checks eligibility. The app must define what account deletion/deactivation does to accepted invitations. |

Required app checks include invalid/expired tokens, cross-tenant access, duplicate
creation, and simultaneous redemption. The built-in `crud`, `compound-index`,
and `unique-index` probes establish only their documented primitive scopes.
They do **not** prove unique-compound behavior or this conditional/concurrent
business flow. Record that additional evidence in the contract.

If the real requirement also creates a membership or account atomically, that
is a different consistency boundary. Verify `multi-document-transactions` and
the real flow, or explicitly redesign before implementation.

## Scope

The contract guides the app's existing validators and integrity checks. It does
not add a universal schema parser, rewrite an ORM's schema, standardize app test
outputs, or automatically repair data. Update the contract and its directly
dependent rules together when the schema changes.
