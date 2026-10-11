# CLAUDE.md

Rules for any Claude Code session in this repo, including the generator's own headless runs.

## What this repo is
A spec-driven generator for messaging clients. The **spec** (`spec/`) says what a client does.
The **harness** (`harness/`, `.claude/`, this file) turns the spec into clients under
`clients/<platform>/` and checks them with `conformance/`. The server (`server/`) is
hand-written. See README.md for the map and PLAN.md for the reasoning.

## Rules
1. **The spec is the source of truth.** Answer behavior questions from `spec/`, never from
   client code. Read `spec/README.md` first; it gives the reading order.
2. **Never hand-edit `clients/`.** Everything there is generated. If a client is wrong, fix
   the spec or the harness and regenerate (`/generate <platform>`). The only exception is the
   generator and fixer agents, which write `clients/<their platform>/` and nothing else.
3. **No silent guessing.** If the spec does not decide something that another client or the
   server could observe (frames, output lines, ordering, errors, timing), stop and ask (in an
   interactive session) or report it (in a generator run). If it only affects code inside one
   client, choose and record it in that client's `ASSUMPTIONS.md`.
4. **Spec changes come with tests.** A behavior change updates `spec/`, bumps the version in
   `spec/README.md`, records the decision in `spec/decisions/`, and adds or updates a scenario
   in `conformance/scenarios/`.
5. **Never weaken a test to make a client pass.** A failing scenario means the client, the
   spec or the scenario is wrong. Find out which; fix that one.
6. **The human owns decisions.** Propose and recommend; flag defaults you had to pick as
   *pending confirmation*; do not decide scope, stack or trade-offs alone.

## Commands
| Task | Command |
|---|---|
| Install Python deps | `python -m pip install -r requirements.txt` |
| Start the server | `python server/server.py --port 8765` |
| Server tests | `python server/test_server.py` |
| Regenerate clients | `/generate all` here, or `python harness/regenerate.py --platform all` |
| Verify existing clients | `/verify all`, or `python harness/verify.py all` |
| Conformance only | `python conformance/run.py [--pair py-ts] [--scenario NAME]` |
| Review the spec for gaps (writes `spec/OPEN_QUESTIONS.md`) | `/review-spec` |
| Resolve open questions with the human, write answers into the spec | `/clarify-spec` |
| Spec gate (any blocking question left?) | `python harness/spec_gate.py` |

## Commits
- Prefixes: `spec:` `harness:` `server:` `test:` `docs:` for hand-crafted work, `gen:` for
  generator output (`clients/` only, never mixed with other changes).
- Add an entry to COLLABORATION_LOG.md for every milestone.
- Commit only when the human asked for it.
