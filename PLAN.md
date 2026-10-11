# Plan — Spec-Driven Messaging Client Generator

## 1. What we are building

This is a **meta-system**, not just a messaging app.

- **The deliverable** is a code generator: a precise spec plus an agentic harness that turns it into
  working clients. If someone deletes the client code and runs the generator, it must recreate
  working clients whose behavior matches the spec.
- **The application** (the evaluation example) is a minimal messaging system: one small server and
  two clients in languages that cannot share source.
- **Core promise:** `delete clients/ → run generator → tests pass`. This is the primary grading criterion.

### Spec vs harness
- **Spec** = *what* to build. It is the source of truth: any behavior question is answered by
  reading the spec, never the code.
- **Harness** = *how* to generate and validate it: project instructions (CLAUDE.md / AGENTS.md),
  commands, sub-agents, prompts, deterministic scripts and the conformance tests.

### Harness, not "multi-agent"
The deliverable is a harness. Sub-agents are used only where they add value:
- **Agents** do the creative and judgment work: generating code per platform (each with an isolated
  context: core spec + its own platform spec), fixing failing tests, and reviewing the spec.
- **Scripts** do everything that must be deterministic: clean, build, test, scenario runner, manifest.
  More agents means more nondeterminism, which works against reproducibility.

## 2. Scope

**In scope**
- A layered spec: core (protocol, client state machine, offline queue, CLI contract, defaults)
  plus platform extensions (Python, TypeScript) plus room for feature extensions.
- A re-runnable generator in Claude Code.
- Two generated clients: Python and TypeScript (Node).
- A trivial server: Python, in-memory, single process, hand-written, not under the generator.
- A language-neutral conformance/scenario test suite.
- Docs: README, DESIGN.md, CLAUDE.md, AGENTS.md, FUTURE.md, attribution.

**Out of scope** (per the assignment)
- Security/auth beyond "identify by name", server persistence, scaling, DDoS protection.
- Cloud or third-party services; messaging/chat SDKs. General-purpose HTTP, WebSocket, JSON and
  storage libraries are allowed.
- Polished UI. The clients are CLIs.

## 3. Inputs and outputs of the generator

```
INPUT                                  GENERATOR                          OUTPUT
spec/core/*.md                         Claude Code:                       clients/<platform>/  (GENERATED)
spec/extensions/*.md          ──►      CLAUDE.md rules +             ──►  + passes conformance matrix
spec/platforms/<lang>.md               /generate command +                + .manifest.json (spec hash, result)
conformance/scenarios/*.yaml           sub-agents + scripts               + ASSUMPTIONS.md
```

## 4. Stack decisions

| Part | Choice | Notes |
|---|---|---|
| Agentic tool | **Claude Code** (Claude Opus 5.5) | Chosen over Codex after the first draft (see COLLABORATION_LOG.md). `AGENTS.md` only points to `CLAUDE.md` |
| Server | Python 3.13, `websockets` (asyncio) | Hand-written, in-memory. `websockets` over FastAPI: simpler for push delivery |
| Client A | Python 3.13 CLI, `websockets` | Generated |
| Client B | TypeScript on Node 24 CLI, `ws` | Generated |
| Transport | WebSocket, JSON frames | Push delivery plus explicit acks; no polling |
| Conformance runner | Python (stdlib + `pyyaml`) | Drives real client processes over stdin/stdout |

Toolchain verified on this machine: Python 3.13.7, Node 24.20, npm 11.19, git 2.33, Claude Code 2.1.

## 5. Repo layout

The folder map, regeneration boundary and attribution are in [README.md](README.md).
This section only lists the planned file breakdown inside `spec/`, which the README doesn't cover:

```
spec/
  README.md          how the spec is layered, versioned and extended
  core/
    00-overview.md   glossary, actors, invariants
    10-protocol.md   wire frames, field types, sequencing, errors
    20-client.md     state machine, login, outbox queue, flush, dedup, display
    30-cli.md        observable contract: stdin commands plus exact stdout lines
    90-defaults.md   rules applied when nothing more specific is stated
  platforms/
    python.md        runtime, libraries, storage, layout, build/run commands
    typescript.md
```

## 6. Spec decisions (to make both clients behave identically)

The assignment scenario (Alice/Bob both go offline, queue, and reconnect at different times) needs
these to be pinned in the core spec:

1. **Message identity:** each message has a client-generated UUID `id`. The server dedups by `id`,
   so flush retries are idempotent.
2. **Send ack:** a message leaves the local outbox only after the server sends `ack{id, seq}`.
3. **Store-and-forward:** the server keeps a mailbox per user. On connect it pushes pending
   messages in `seq` order and deletes each one only after the client's `deliver_ack`.
   This is what lets Bob receive Alice's message after *he* reconnects.
4. **Ordering:** the outbox flushes FIFO (one in flight vs pipelined: decide in spec). Received
   messages are displayed in server `seq` order, and the client dedups by `id`.
5. **Persistence:** the outbox is stored in a local file per user and survives a client restart.
6. **Offline simulation:** `/offline` closes the socket and suppresses reconnect; `/online`
   reconnects. This is deterministic, so the scenario can be tested.
   (Not "retry on an interval when a network call fails", which is untestable.)
7. **Login:** `/login <name>` on first launch. Spec defines name rules and the policy for a
   second session with the same name.
8. **Observable output:** an exact, line-based stdout format (e.g. `RECV from=alice id=… text=…`,
   `QUEUED id=…`, `SENT id=…`, `STATE online|offline`) so the two clients' output can be compared.

## 7. Handling unclear specs

The generator must never ask questions at run time: graders run it unattended, and a chat answer
is not reproducible. Clarification happens before generation and is written into the spec.

| Phase | Who | Interactive? | Output |
|---|---|---|---|
| 1. Spec authoring and clarification | Author + spec-reviewer agent (`/clarify-spec`) | Yes | Decisions written into `spec/` and `spec/decisions/` |
| 2. Generation | Harness + agents only | No (headless, repeatable) | Code, test results, `ASSUMPTIONS.md` |

- **Gate before generation:** the spec-reviewer checks the spec against a checklist (identity,
  acks, ordering, offline triggers, retries, display format, error cases) and writes
  `OPEN_QUESTIONS.md`. Generation refuses to run while it has blocking items.
- **No silent guessing (CLAUDE.md rule):**
  - If behavior visible across clients is ambiguous (wire format, ordering, output): fail the run
    with a clear question.
  - If something internal to one platform is ambiguous (names, which storage library): choose,
    and log it in `clients/<p>/ASSUMPTIONS.md`.
  - Defaults in `spec/core/90-defaults.md` resolve common gaps the same way every time.
- **After generation:** conformance tests and cross-client output comparison catch what review
  missed. Every failure becomes a **spec fix**, never a hand edit of generated code.

```
author spec ─► /clarify-spec (interactive) ─► decisions written into spec
                                                  │
                    ┌─────────────────────────────┘
                    ▼
       spec-review gate ── open questions? ──► yes: back to the author
                    │ no
                    ▼
       generate (headless) ── blocking ambiguity? ──► fail and report the question
                    │
                    ▼
       tests + cross-client diff ── divergence? ──► spec gap: fix the spec, regenerate
                    │ pass
                    ▼
                  done (ASSUMPTIONS.md lists minor choices)
```

## 8. Generation pipeline

```
/generate <python|typescript|all>
  1. gate      OPEN_QUESTIONS.md empty and spec-reviewer passes, else stop
  2. clean     harness/clean.py    — delete clients/<p>/
  3. generate  client-generator sub-agent per platform (isolated context:
               spec/core + spec/extensions + spec/platforms/<p>.md only)
  4. verify    harness/verify.py   — install, build, unit tests, conformance matrix
  5. fix       client-fixer sub-agent with failures + spec, max 3 rounds
  6. record    harness/manifest.py — spec hash, result, ASSUMPTIONS.md
```
The headless equivalent, `harness/regenerate.py`, wraps `claude -p`; usage is in the README.

## 9. Quality strategy
- **Conformance scenarios are executable spec**, run as a matrix: py↔py, ts↔ts, py↔ts, ts↔py.
- **Cross-client diff:** run the same scenario on both clients and compare normalized transcripts.
- **Clean-room regeneration:** delete → regenerate → verify, at least twice.
- **Evolution test:** add a spec module and regenerate with no harness changes.
- No manual-only testing: if it isn't in a scenario, it isn't verified.

## 10. Build approach: vertical slices through the spec

Each slice is a **spec change followed by a full regeneration from scratch**, never a patch on
existing generated code. This proves the harness handles an evolving spec and produces a
readable commit history.

- **Spec v1:** login + send + receive (online only) → generate both clients.
- **Spec v2:** offline outbox, acks, store-and-forward, Alice/Bob scenario → delete and regenerate.
- **Spec v3 (stretch):** one extension module (reactions or read receipts) → regenerate, no harness edits.

## 11. Schedule (12-hour budget)

| Hours | Work | Commit prefixes |
|---|---|---|
| 0–1 | Repo setup, CLAUDE.md/AGENTS.md, **spec v1 core** (protocol, CLI contract), platform specs | `spec:` `harness:` |
| 1–2 | Server + conformance runner + basic messaging scenario | `server:` `test:` |
| 2–4 | Generator (clean/generate/verify/fix) → **Python client** passes tests | `harness:` `gen:` |
| 4–5 | **TypeScript client** from the same spec → all four pairings pass | `gen:` |
| 5–7 | **Spec v2:** offline outbox + server mailbox + Alice/Bob scenario → regenerate both | `spec:` `test:` `gen:` |
| 7–8 | Clean-room regeneration ×2, headless script | `harness:` |
| 8–9 | *(Stretch)* **Spec v3** extension demo | `spec:` `gen:` |
| 9–11 | README (map + attribution), DESIGN.md, FUTURE.md | `docs:` |
| 11–12 | Buffer, fresh-clone check, zip | |

Docs are started at hour 0 and filled in as we go, not written only at the end.

**Cut order if behind:**
1. The spec v3 extension demo → describe it in FUTURE.md instead.
2. The separate spec-reviewer agent → fold it into a checklist in CLAUDE.md.

**Never cut:** the re-runnable generator command and the automated conformance tests.

## 12. Deliverables checklist
- [ ] Repo zipped, with clear top-level folders
- [ ] `README.md`: where the harness, spec, generator, generated code and server are; how to regenerate; attribution
- [ ] `DESIGN.md`: design principles
- [ ] `CLAUDE.md` + `AGENTS.md`
- [ ] `spec/`: source of truth
- [ ] `.claude/` + `harness/`: commands, agents, scripts
- [ ] `clients/python/`, `clients/typescript/`: generated, committed, boundary marked
- [ ] `server/`: hand-written
- [ ] `conformance/`: scenarios + runner
- [ ] `FUTURE.md`
- [ ] Commit history that tells the story (no single final drop)

## 13. Attribution policy
Defined in the README ("Regeneration boundary"). Rule of thumb: `clients/` is generated and never
hand-edited, and everything else is hand-crafted (human-led, AI-assisted).
