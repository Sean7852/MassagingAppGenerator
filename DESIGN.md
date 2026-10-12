# Design — Spec-Driven Messaging Client Generator

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

```
README.md                 start here: where everything is, how to run, test and regenerate
DESIGN.md                 this document: goals, decisions, pipeline, quality strategy
FUTURE.md                 what we would do next
COLLABORATION_LOG.md      who did what (human vs AI), per milestone
CLAUDE.md                 rules for every Claude Code session, including the generator's
AGENTS.md                 points other agent tools to CLAUDE.md
Assignment                the original assignment text
requirements.txt          Python packages for the server, tests and harness

spec/                     SOURCE OF TRUTH: what the clients do
  README.md               how the spec is layered, versioned and extended; reading order
  core/                   shared by every client
    00-overview.md        terms, actors, invariants, scope
    10-protocol.md        WebSocket frames between client and server
    20-client.md          client states, login, outbox, sending, receiving
    30-cli.md             exact commands and output lines (friendly and --machine)
    40-storage.md         the saved state file (name and outbox)
    90-defaults.md        rules for anything not covered elsewhere
  extensions/
    10-read-receipts.md   v3 feature module
  platforms/
    python.md             how to build the client in Python (libraries, layout, pitfalls)
    typescript.md         how to build the client in TypeScript on Node.js
  decisions/README.md     every decision, who made it, and why
  OPEN_QUESTIONS.md       must have no open blocking item before generation

harness/                  deterministic generator scripts
  regenerate.py           the pipeline: gate, clean, generate, verify, fix, manifest
  verify.py               build, unit tests and conformance for existing clients
  spec_gate.py            refuses generation while a blocking question is open
  clean.py                deletes a generated client
  manifest.py             records which spec a client came from; detects stale clients
  platforms.py            reads build/test/run commands from spec/platforms/*.md
.claude/
  commands/               /generate, /verify, /review-spec, /clarify-spec
  agents/                 client-generator, client-fixer, spec-reviewer
.agents/, .codex/         the same commands and agents for Codex

server/                   hand-written Python WebSocket server, in memory
  server.py
  test_server.py          protocol tests (no clients needed)

conformance/              hand-written, language-neutral tests
  run.py                  starts the server and real clients, checks their output
  scenarios/*.yaml        12 scenarios, incl. the assignment's Alice/Bob offline scenario

clients/                  ===== GENERATED: regeneration boundary, never edited by hand =====
  python/                 Python client (+ GENERATED.md, ASSUMPTIONS.md, .manifest.json)
  typescript/             TypeScript client (same files)
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
| 1. Spec authoring and clarification | Author + spec-reviewer agent (`/review-spec`, then `/clarify-spec`) | Yes | Decisions written into `spec/` and `spec/decisions/` |
| 2. Generation | Harness + agents only | No (headless, repeatable) | Code, test results, `ASSUMPTIONS.md` |

- **Review, then gate:** `/review-spec` runs the spec-reviewer, which checks the spec against a
  checklist (identity, acks, ordering, offline triggers, retries, display format, error cases)
  and writes `OPEN_QUESTIONS.md`. `/clarify-spec` resolves the items with the author. Generation
  refuses to run while the file has blocking items. The review itself is a manual step, not part
  of the gate: running an AI review on every generation would make generation less repeatable,
  so the gate (`harness/spec_gate.py`) only reads the file.
- **No silent guessing (CLAUDE.md rule):**
  - If behavior visible across clients is ambiguous (wire format, ordering, output): fail the run
    with a clear question.
  - If something internal to one platform is ambiguous (names, which storage library): choose,
    and log it in `clients/<p>/ASSUMPTIONS.md`.
  - Defaults in `spec/core/90-defaults.md` resolve common gaps the same way every time.
- **After generation:** conformance tests and cross-client output comparison catch what review
  missed. Every failure becomes a **spec fix**, never a hand edit of generated code.

```
author spec ─► /review-spec ─► /clarify-spec (interactive) ─► decisions written into spec
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
  1. gate      no blocking item in OPEN_QUESTIONS.md, else stop (harness/spec_gate.py)
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

Docs are started at hour 0 and filled in as we go, not written only at the end.

## 11. Attribution policy
Defined in the README ("Regeneration boundary"). Rule of thumb: `clients/` is generated and never
hand-edited, and everything else is hand-crafted (human-led, AI-assisted).


## 12. Conclusion

**The result.** The generator worked as promised. Three versions of the spec were turned into
working Python and TypeScript clients: v1 (login, send, receive), v2 (offline messaging, the
assignment's Alice/Bob scenario) and v3 (read receipts, added as an extension module). Each
time the clients were deleted and regenerated from scratch, and each time they passed every
test in all four language pairings without a single fix round. v3 needed no change to the
harness at all.

**Where the human effort went.** Writing code was not the hard part; making the spec
unambiguous was. Most of the human author's time went into deciding how the chat app should
behave wherever two careful implementers could have done it differently:

- **Chat behavior:** what "going offline" means and how to come back; what the user sees when
  sending a message, and when it counts as sent; logging in once and being remembered;
  what happens to commands typed while connecting; what is saved on disk and what to do if
  that file is damaged; when a message is too long; how a dead connection is noticed;
  read receipts; and making the output readable for people while staying exact for tests.
- **Language differences:** Python and JavaScript quietly disagree on details such as line
  endings, rare invisible characters, invalid text, command-line options and the defaults of
  their WebSocket libraries. For each, the human chose one rule that both clients must follow.
- **Direction:** the stack, the scope, one generation path, keeping the spec review a manual
  step, and which feature to add as the extension.

**What the AI did.** It drafted the spec and laid out each open question with options and a
recommendation. It built the harness (the generation pipeline, the agents and commands, the
verification scripts), the conformance test runner and scenarios, and the server with its
tests. It ran the generator, checked the generated code, and wrote the first drafts of the
documentation. Its own mistakes, three wrong platform rules, were caught by the spec review
and by the generator itself before they reached the main branch.

**Readability.** The human author reworked the README and this document so that they read as
the author's own reasoning rather than as a record of every detail. The full list of decisions
remains in `spec/decisions/README.md` for anyone who needs it.
