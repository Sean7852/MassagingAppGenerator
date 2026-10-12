# Decisions

Every decision behind the spec, in one list. Each says who made it and when.
"Human" is the human author. "On AI recommendation" means the AI proposed it and the human
chose it. A decision that was replaced stays in the list, marked as replaced.

Status: **in force**, **replaced** (by a later decision), or **spec pending** (decided, not yet
written into the spec modules).

## Protocol and server

| # | Decision | Why | By | Status |
|---|---|---|---|---|
| D1 | Transport is WebSocket, one JSON object per text frame. | The server can push messages; no polling. | Human (stack choice), 2026-10-11 | in force |
| D2 | Each message is identified by (sender, client-generated lowercase UUID v4). The server ignores duplicates. | Makes resending safe, which the offline outbox relies on. | AI default, accepted by human, 2026-10-11 | in force |
| D3 | Names match `^[a-z0-9_]{1,32}$` and only the server checks them. | One authority, so the clients cannot disagree. | Human, on AI recommendation, 2026-10-11 | in force |
| D4 | A second login with the same name replaces the older connection. | A client that dropped without a clean close can log in again at once. | Human, on AI recommendation, 2026-10-11 | in force |
| D5 | Messages to a name that has never logged in are accepted and held. | Users exist by name only; there is no registration. | Human, on AI recommendation, 2026-10-11 | in force |

## Sending, offline and reconnecting

| # | Decision | Why | By | Status |
|---|---|---|---|---|
| D6 | The outbox is sent one message at a time (one waiting for the server's confirmation). | The smallest state machine to specify and to generate identically in two languages; order is automatic. | Human, on AI recommendation, 2026-10-11 | in force |
| D10 | ~~A lost connection reports each unsent message as `ERROR code=not_sent`.~~ | v1 had no outbox. | AI default, 2026-10-11 | replaced by D14 |
| D13 | Every `/send` prints `QUEUED` at once (online or offline), then `SENT` when the server confirms. | The same lines whatever the connection state at that instant, so output never depends on timing. | Human, on AI recommendation, 2026-10-11 | in force |
| D14 | A lost connection leaves the client offline with its outbox kept; it reconnects only on `/online`. No automatic retry. | Deterministic and testable; nothing is lost. | Human, on AI recommendation, 2026-10-11 | in force |
| D16 | `/offline` drops the connection (printing that it did) and `/online` reconnects: simulated network loss, not a protocol feature. | The assignment's scenario needs exact offline and online moments. | Human, on AI recommendation, 2026-10-11 | in force |
| D20 | A command that does not fit the current state gets its own error: `already_online`, `already_offline`, `already_logged_in`, and `not_logged_in` before any login. | Every command in every state has exactly one visible outcome. | Human, on AI recommendation, 2026-10-11 | in force |

## Identity and saved state

| # | Decision | Why | By | Status |
|---|---|---|---|---|
| D9 | ~~In v1 the name is typed with `/login` on every launch.~~ | v1 kept nothing on disk. | AI default, 2026-10-11 | replaced by D12 |
| D12 | With a saved name, the client logs in by itself at startup (as if `/online` was typed). | The assignment asks for login "on first launch"; later launches should not ask again. | Human, on AI recommendation, 2026-10-11 | in force |
| D15 | The saved state has one exact format, `<data-dir>/state.json` (`version`, `name`, `outbox`), written atomically before the line that reports the change. | Both clients store the same thing the same way; inspectable; a printed line means the change is on disk. | Human, on AI recommendation, 2026-10-11 | in force |
| D17 | The data directory is `--data-dir`, default `.msgdata` in the current folder. One data directory belongs to one user; `/login` works only when no name is saved (no logout, no switching users). | The smallest model that covers the assignment. Two users on one machine use two data directories. | Human, on AI recommendation, 2026-10-11 | in force |
| D18 | A saved file that cannot be read or is invalid makes the client exit with status 1 (message on stderr), leaving the file untouched. | Unsent messages are never thrown away silently. | Human, on AI recommendation, 2026-10-11 | in force |
| D19 | Shown messages are remembered only while running. After a restart a message may, rarely, be shown again. | A duplicate needs a lost confirmation at the moment of a restart; saving every id forever is not worth it. | Human, on AI recommendation, 2026-10-11 | in force |

## Output and errors

| # | Decision | Why | By | Status |
|---|---|---|---|---|
| D7 | Two output modes. By default the client prints **friendly text** for humans. With `--machine` it prints the fixed keyword lines (`SENT id=… seq=… to=…`), which the tests use. **Both** modes are exactly specified, so both clients look identical in either mode. (Changed: v1 had only the keyword lines.) | Pleasant for people, and still comparable character by character for tests. | Human, 2026-10-11 | spec pending |
| D8 | Errors the client raises itself have fixed codes **and** fixed wording. | Both clients print identical lines, not just identical codes. | Human, on AI recommendation, 2026-10-11 | in force |

## Platforms

| # | Decision | Why | By | Status |
|---|---|---|---|---|
| D11 | Platform modules pin exact libraries and versions (`websockets` 15; `ws` 8, TypeScript 5.9) and spell out the I/O pitfalls: stdin on each OS, UTF-8, flushing, exiting, library settings that change behavior. | These are where generated code most often breaks or differs between runs. The pinned details must be correct (the v2 review found two to fix). | Human, on AI recommendation, 2026-10-11 | in force |
