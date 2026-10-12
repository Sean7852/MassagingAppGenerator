# Design

The principles behind this generator, why we chose them, and where to see each one at work in
the repo. The plan and schedule are in [PLAN.md](PLAN.md); every individual decision is in
[spec/decisions/README.md](spec/decisions/README.md).

## What the design optimizes for

1. **Regeneration works.** Delete `clients/`, run the generator, get working clients back.
   Every time, not just once.
2. **Two languages, one behavior.** The Python and TypeScript clients cannot share code, yet
   they must be indistinguishable from outside: the same output, byte for byte.
3. **The spec can grow.** New features arrive as new spec modules, without rewriting the
   harness.

Every principle below serves at least one of these.

---

## 1. The spec is the source of truth

**Rule.** Behavior is defined in `spec/` and nowhere else. A question about how a client
behaves is answered by reading the spec, never the code. If a client is wrong, the fix goes
into the spec (or the harness), followed by a regeneration.

**Why.** A generator is only reproducible if its input is complete. The moment people fix the
code by hand, the spec stops describing the product.

**In the repo.** `clients/` is never edited by hand (CLAUDE.md, rule 2). When the TypeScript
generator found that a platform rule was wrong (Node's `readline` splits lines at U+2028), we
did not patch the client: we fixed the spec (D35), and the next regeneration matched it.

## 2. Separate *what* from *how*

**Rule.** The spec has three layers. **Core** modules say what every client does, and never
name a language. **Platform** modules say how to do it in one language, and never change
observable behavior. **Extension** modules add features, and say which core rules they extend.

**Why.** Two generators working from the same core cannot drift apart on behavior. A platform
module can pin the risky details of one runtime without leaking into the other.

**In the repo.** `spec/core/`, `spec/platforms/python.md` and `typescript.md`,
`spec/extensions/`. A client for platform *P* is generated from core + extensions + *P* only.

**Lesson learned.** Platform modules pin libraries and known pitfalls: stdin on Windows,
UTF-8, flushing, exiting (D11). That made runs predictable, but the pinned details must be
right. Three of ours were wrong (B8, B12, D35), and the review and the generator caught all
three before they reached `main`.

## 3. Specify what can be observed exactly; leave the rest free

**Rule.** Anything another client, the server or a user could observe is specified exactly:
every output line, field order, escaping, error code *and* wording, every frame, every state
transition. Anything invisible from outside is left to the generator and recorded in
`clients/<p>/ASSUMPTIONS.md`.

**Why.** "Behaves identically" is only testable if behavior is exact. Over-specifying internals
would make the spec long and brittle for no gain.

**In the repo.** `spec/core/30-cli.md` defines every machine line and every friendly line.
Client-side errors have fixed messages (D8). The test for each spec sentence: *could two careful
implementers do this differently, in a way someone could see?* If yes, the spec decides.

## 4. Prefer determinism to realism, and say so when we don't

**Rule.** Where a realistic behavior would depend on timing, choose a deterministic one that
can be tested exactly.

**Why.** A behavior that cannot be tested identically across two clients cannot be proven
identical.

**In the repo.**
- Going offline is a command (`/offline`, `/online`), not a timer (D16).
- A lost connection waits for `/online` instead of retrying on a schedule (D14).
- Every `/send` prints `QUEUED`, online or not (D13).
- The outbox sends one message at a time (D6).
- Going online holds other commands until the login outcome is known (D21).

The one deliberate exception is keep-alive pings (D31). They are timing-based and not
tested quickly, but without them a client would never notice a dead network. That trade-off
is written down.

## 5. Clarify before generating, never during

**Rule.** Questions about behavior are answered by a human, before generation, and the
answers are written into the spec. Generation itself never asks anything: it can run unattended.

**Why.** A chat answer during generation is not reproducible: the next run would not know it.
An answer in the spec is.

**In the repo.**
- `/review-spec` runs the `spec-reviewer` agent, which lists gaps in `spec/OPEN_QUESTIONS.md`.
- `/clarify-spec` walks the human through them.
- The generator refuses to start while a blocking question is open (`harness/spec_gate.py`).
- If a generator still finds a gap, it writes `BLOCKED.md` and stops instead of guessing.

For v2 the reviewer found 13 blocking gaps. The human decided each one (D21–D32).

We chose to keep the review a manual step, not part of every generation. An AI review on
every run could raise a new question on an unchanged spec, and a reviewed spec would then stop
regenerating.

## 6. Scripts decide, agents create

**Rule.** AI agents do only what needs judgment: writing a client, fixing a failing one,
reviewing the spec. Everything that must be repeatable is a plain script: the gate, cleaning,
building, testing, verifying, recording.

**Why.** Every AI step adds variation between runs. Keeping them few and surrounded by
deterministic checks keeps the pipeline repeatable.

**In the repo.** `harness/regenerate.py` runs the pipeline: gate → clean → generate → verify
→ fix (at most 3 rounds) → manifest → cross pairings. There is **one** generation path:
`/generate` in Claude Code just runs that script, so the slash command and the terminal can
never behave differently.

## 7. Fence the agents, and check the fence

**Rule.** Each agent can read only what it needs and write only its own folder. After every
agent run, a script checks that nothing outside that folder changed.

**Why.** The regeneration boundary has to hold by construction, not by trust.

**In the repo.**
- The generator for platform *P* cannot read the other client or the server, and can only
  write `clients/<P>/` (permission deny rules).
- `harness/regenerate.py` compares `git status` before and after each agent run, and fails
  the run on any change outside the fence.
- Every generated source file starts with a `GENERATED` header; `verify.py` checks it.

The check once failed a run because the interactive Claude session edited README.md while the
generator was running. The generator itself had written nothing outside its folder, but the
check cannot tell who made a change, so failing was correct. The rule since: don't edit files
during a run.

## 8. Tests are executable spec, judged across languages

**Rule.** Behavior is verified by running the real clients against the real server and
comparing their output line by line, in every pairing of languages.

**Why.** A Python client talking to a Python client proves little about identical behavior.
Mixing them proves the protocol and the output agree.

**In the repo.**
- `conformance/run.py` starts a fresh server and real client processes, types commands, and
  checks every line.
- Every scenario runs as py↔py, ts↔ts, py↔ts and ts↔py.
- Scenarios are designed to have one correct order. For example, they queue messages while
  offline first, so `QUEUED` and `SENT` cannot race. They accept either order only where the
  spec says timing may vary (receipts arriving during a flush).
- The server has its own protocol tests (`server/test_server.py`).
- Nothing counts as verified unless a test runs it.

## 9. Regenerate; never patch

**Rule.** Every spec version is a full regeneration from an empty folder, not an edit of the
previous code.

**Why.** It proves the core promise at every step, not only at the end.

**In the repo.** v1, v2 and v3 were each regenerated from scratch. Each client records the
spec hash it came from in `.manifest.json`, and `python harness/manifest.py --check all`
reports a client generated from an older spec. It caught the TypeScript client after D35.

## 10. Evolve by adding modules

**Rule.** A new feature is a new extension module that adds to the core. The core already
tells every client to ignore message types it does not know, so old clients keep working.

**Why.** "Evolution" means the harness handles specs it has never seen.

**In the repo.** v3 added read receipts as `spec/extensions/10-read-receipts.md`. Between
`main` before v3 and after it, **nothing** in `harness/`, `.claude/`, `CLAUDE.md` or the platform
modules changed. The generators built the feature with 0 fix rounds, and the v2 clients still
passed every scenario that expected no receipt.

## 11. Humans decide; AI proposes and records

**Rule.** Scope, trade-offs and behavior are human decisions. The AI proposes options with a
recommendation, flags any default it had to pick as *pending confirmation*, and records who
decided what.

**Why.** The grading asks what was ours and what was delegated. The record also makes the spec
explainable: every rule has a reason and an owner.

**In the repo.**
- [spec/decisions/README.md](spec/decisions/README.md) lists D1–D39, each with who decided and
  its status.
- [COLLABORATION_LOG.md](COLLABORATION_LOG.md) records each milestone.
- Commit prefixes separate hand-crafted work (`spec:`, `harness:`, `server:`, `test:`, `docs:`)
  from generator output (`gen:`).

---

## Trade-offs we accepted

| Choice | We gave up | Why it was worth it |
|---|---|---|
| A command-line client, not a GUI | A pleasant interface | Exact, scriptable tests in both languages. A GUI can be a thin layer later (see [FUTURE.md](FUTURE.md)). |
| Friendly output plus a `--machine` mode | One output format to specify | Readable for people, still byte-comparable for tests (D7). |
| Going online holds other commands (D21) | Responsiveness for up to 5 s when the server is down | One simple rule; no ordering differences between clients. |
| No automatic reconnect (D14) | Convenience | Deterministic, testable offline behavior. |
| Keep-alive pings (D31) | Full test coverage | Detects a dead network; the gap is documented. |
| Pinned libraries and platform rules (D11) | Generator freedom | Fewer differences between runs, as long as the pins are correct. |
| Claude Opus for generation | Cost per run | Zero fix rounds in every generation so far. |
| In-memory, trusting server | Persistence, security | Out of scope by the assignment; kept simple and hand-written. |

## How we know it works

| Spec version | Clients | Fix rounds | Conformance |
|---|---|---|---|
| v1: login, send, receive | Python, TypeScript | 0 | 28/28 (7 scenarios × 4 pairings) |
| v2: offline outbox, saved state, `/offline`, `/online`, friendly output | Python, TypeScript | 0 | 44/44 (11 × 4) |
| v3: read receipts (extension) | Python, TypeScript | 0 | 48/48 (12 × 4) |

Each row is a regeneration from empty `clients/` folders, followed by independent verification.
The quality comes from layers, each catching what the one before it missed: an exact spec, a
spec review, generators that stop instead of guessing, a scripted boundary check, and tests
across languages.
