# First-user journeys

The campaign entry point is the root README. It must lead to a useful application
and verifiable evidence, not a skills catalog or an untested installation claim.
The landing page itself is outside this kit's scope.

## Journey 1: "Let me see it working"

| Stage | Developer action | Required success gate |
| --- | --- | --- |
| Arrive | Read the root README; choose the small starter or a real gallery app | Clear use case, prerequisites, and local-development boundary |
| Prepare | Install Docker/Compose and Python, start Linux containers, clone the kit | Local Docker works; package/image HTTPS is available |
| Start | Run `python3 quickstart.py` | Reviewed dependencies download; database/API become healthy |
| Verify | The startup command runs real HTTP CRUD and integrity checks | Persisted reads, invalid-write rejection, database execution/storage evidence, and a nonzero exit on failure |
| Try it | Create/list a task, or follow a gallery app's user journey | A usable local application, not just a successful database ping |
| Return | Rerun the same command | Same credentials/data, cached verified dependencies, checks rerun |
| Recover | Use `--app-port` / `--db-port` for conflicts; correct Docker/network problems | No silent TLS disabling, credential regeneration, or destructive reset |
| Stop | Run `python3 quickstart.py stop` | Only this project stops; its data/private `.env` remain |

The startup output prints the actual app URL, check/request counts, integrity
coverage, selected database timings, and report locations. Full raw evidence is
in `.runtime/`; generated credentials stay in `.env`. Both are ignored by Git.
An empty running-app collection is reported honestly; the disposable E2E
database separately proves the write path.

For meaningful application experiences, follow the independently runnable
NodeBB, HeyForm, or Parse feedback examples in the samples gallery. Each has
`python3 run.py` and a separate `python3 run.py verify` that creates disposable
services, exercises real user operations, restarts services, and removes only
its own test resources.

## Journey 2: "Build my application with my agent"

1. Open your coding agent in the kit checkout and use the root README's prompt.
   No MCP installation, agent-specific plugin, cloud token, or routing helper
   is required.
2. The agent confirms the user flows and existing stack, checks prerequisites,
   and runs `python3 quickstart.py database` for a new custom app. It does not
   force the Python task app or its drivers onto another stack. Reuse an
   explicitly chosen existing dev database or a gallery app's own setup.
   If Docker/HTTPS access is unavailable, state the blocker.
3. Select a useful gallery integration when appropriate. For a custom app, work
   in an explicit new application directory or the user's existing project,
   never overwrite unrelated files or the kit's starter.
4. Before coding, fill [the app-owned contract](APP-CONTRACT.md): document
   shape/BSON types, growth bounds, embedding/reference reasons, invariants,
   indexes tied to actual queries, and image-qualified capability requirements.
   Run [only required feature probes](COMPATIBILITY.md); unknown combinations
   need app-specific evidence. Do not silently downgrade unsupported features.
5. Implement the smallest useful user flow with validated writes and bounded
   reads. Reuse its contract in a read-only integrity check.
6. Start the actual app, exercise its real HTTP/UI workflow, read back persisted
   state, reject invalid operations, and record genuine database-side metrics
   against its actual query shapes.
7. Hand over the app URL, setup command, schema reasons, integrity scope/report,
   E2E command/report, and known limitations. Generated code or mocked tests are
   not a completion gate.

The kit guides arbitrary stacks; it does not promise unattended scaffolding for
every framework or install/operate the coding agent itself. Extra dependencies
introduced by a custom app belong in that app's manifest/container, not hidden
global installation steps.

## Failure experience

- Missing Docker/old Compose/wrong container architecture: print actionable
  prerequisite guidance and stop before claiming readiness.
- Registry/PyPI/proxy/CA problem: fail the download or hash check. Preserve
  credentials; do not set insecure package trust or turn off certificate checks.
- Port conflict: explicit port flags update only ports, retaining credentials.
- Failed HTTP/database/integrity assertion: return nonzero and retain its
  machine-readable report. Do not repair data.
- Incomplete integrity coverage: never label it a global integrity pass.
- Cleanup failure: report failure rather than hide orphaned test resources.

Docker/Python installation, trusted production TLS, deployments, authentication
for the small task API, backups, and capacity planning remain explicit boundaries.
This is a development kit, not a production-readiness certification.

## Campaign publication gate

Before enabling an advertisement:

1. Publish the reviewed kit and gallery changes; verify the actual landing-page
   destination/clone URLs resolve to those versions, not an empty or older repo.
2. Run the documented commands from a clean checkout on the campaign's advertised
   platform. CI covers Linux amd64; arm64/Windows/macOS need platform-specific
   validation before promising identical support.
3. Require the kit's cold-start CI and the gallery's integration CI to pass.
   Review live browser behavior as well as API/database results.
4. Check each registered sample's README, environment template, license,
   successful user flow, restart persistence, and cleanup.
5. Keep copy honest: dependencies are downloaded after host prerequisites;
   setup time depends on network/resources; local development is not production.
   A third-party app's untested plugins/providers/features are not certified.
