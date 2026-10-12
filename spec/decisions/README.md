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
| D7 | Two output modes. By default the client prints **friendly text** for humans. With `--machine` it prints the fixed keyword lines (`SENT id=… seq=… to=…`), which the tests use. **Both** modes are exactly specified, so both clients look identical in either mode. (Changed: v1 had only the keyword lines.) | Pleasant for people, and still comparable character by character for tests. | Human, 2026-10-11 | in force |
| D8 | Errors the client raises itself have fixed codes **and** fixed wording. | Both clients print identical lines, not just identical codes. | Human, on AI recommendation, 2026-10-11 | in force |

## Platforms

| # | Decision | Why | By | Status |
|---|---|---|---|---|
| D11 | Platform modules pin exact libraries and versions (`websockets` 15; `ws` 8, TypeScript 5.9) and spell out the I/O pitfalls: stdin on each OS, UTF-8, flushing, exiting, library settings that change behavior. | These are where generated code most often breaks or differs between runs. The pinned details must be correct (the v2 review found two to fix). | Human, on AI recommendation, 2026-10-11 | in force |

## From the review of spec v2 (2026-10-12)

The spec-reviewer agent found 13 blocking questions (B1–B13 in
[../OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md)). The human decided each one.

| # | Decision | Why | By | Status |
|---|---|---|---|---|
| D21 | **Going online holds everything up** (B1, B2): from `/online`, `/login` or startup until the login outcome is known, no other command is handled; commands typed meanwhile wait, in order. The open timeout is 5 s. So no command ever sees the `connecting` state, which removes B1. | One simple rule; the two clients cannot order lines differently while connecting. Cost: `/offline` cannot cancel a slow attempt (at most 5 s). | Human (chose "hold up" over the AI's "background"), 2026-10-12 | in force |
| D22 | Anything arriving from a connection that is no longer the current one is ignored; while `idle` or `offline` every frame is ignored; while `connecting` only `login_ok` and `error` count (B3). | Leftovers from a closed connection cannot print stray lines; ignored deliveries are redelivered by the server. | Human, on review recommendation, 2026-10-12 | in force |
| D23 | A server frame of a known type with a missing or wrong-typed field is ignored entirely: no output, no `deliver_ack` (B4). `seq` is a whole number 1..2^53−1; `ref: null` counts as absent. | One defined outcome instead of "crash" in one client and "print undefined" in the other. | Human, on review recommendation, 2026-10-12 | in force |
| D24 | Lone surrogates in received text or messages are printed as U+FFFD (B5). | Both clients print the same character instead of one failing. | Human, on review recommendation, 2026-10-12 | in force |
| D25 | The command table is written in plain words, not regexes: the `/send` text is "everything after the name and one space, to the end of the line, whatever characters it contains" (B6). | Python and JavaScript regexes disagree on rare characters such as U+2028. | Human, on review recommendation, 2026-10-12 | in force |
| D26 | Invalid UTF-8 on stdin is read as U+FFFD and the line is handled normally (B7). | The Python client would otherwise stop reading input. | Human, on review recommendation, 2026-10-12 | in force |
| D27 | The Python platform sets universal newlines explicitly (`newline=None`) so a lone `
` ends a line on every OS (B8). | The previous rule was only correct on Windows (AI error, found by the review). | Human, on review recommendation, 2026-10-12 | in force |
| D28 | Exact argument grammar: only `--server`, `--data-dir` (value as next argument or after `=`, not empty) and `--machine`, each at most once; anything else, including `-h` and shortened options, is exit 2; arguments are checked before the saved state (B9). | Python's and Node's argument libraries differ by default. | Human, on review recommendation, 2026-10-12 | in force |
| D29 | Strict validity rules for `state.json`, including the message-id format; anything else makes the client exit 1 (B10, with D18). | Hand edits or damage are noticed instead of guessed at; a bad id can no longer stall the outbox forever. | Human, on review recommendation, 2026-10-12 | in force |
| D30 | `/send` refuses a text over 8192 bytes of UTF-8 locally with `ERROR code=too_long message=message too long (max 8192 bytes)`; nothing is queued (B11). | A frame over 64 KiB makes the server drop the connection on every retry, blocking the outbox. Bytes count the same in both languages. | Human, on AI recommendation, 2026-10-12 | in force |
| D31 | Both clients send a WebSocket ping every 20 s and treat a missing pong (20 s) as a lost connection; no HTTP proxy; HTTP redirects out of scope (B12). | Notices a network that died without closing the connection, so a waiting message is not stuck forever. Not testable quickly; checked by reading the code. | Human (chose pings over the AI's "no pings"), 2026-10-12 | in force |
| D32 | Signals (Ctrl+C, SIGTERM) and a closed stdout are out of scope: not specified, not tested (B13). | Neither generator invents behavior; can be specified later. | Human, on review recommendation, 2026-10-12 | in force |
| D33 | The exact friendly wording: `Logged in as <name>`, `[queued] to <to>: <text>`, `[sent]   to <to> (#<seq>)`, `[<from>] <text>`, `Error: <message>`, `You are offline. Messages will be queued.`, `Disconnected. Type /online to reconnect.`, `Bye.` | Follows the preview the human picked for D7. | AI default, pending confirmation | in force |
| D34 | Small clarifications from the non-blocking review items: "opened" means the WebSocket handshake completed, with a 5 s timeout, in core (N1); both platforms fsync before renaming (N2); unknown fields in `state.json` are dropped on the next save (N3); values other than text and message are written unescaped (N4); binary frames are ignored and a `deliver`'s `to` is not checked (N6); how each platform exits mid-run (N7); `already_online`'s message becomes `already online`, since `connecting` is no longer visible. | Each removes a small guess; none changes normal behavior. | AI default, pending confirmation | in force |
| D35 | The TypeScript client splits stdin lines itself instead of using `node:readline`, which also ends lines at U+2028/U+2029 and so broke D25. | Found by the TypeScript generator during the v2 generation (it deviated from the platform rule to keep the core behavior and reported it); verified by hand. An AI error in the platform rule. | AI, found by the generator, 2026-10-12 | in force |

## Spec v3: read receipts (2026-10-12)

| # | Decision | Why | By | Status |
|---|---|---|---|---|
| D36 | v3 adds **read receipts** as an extension module, `spec/extensions/10-read-receipts.md`, with no changes to the harness. | Shows that the harness handles a new spec module (the assignment's "evolution" criterion). | Human, on AI recommendation, 2026-10-12 | in force |
| D37 | Receipts are **automatic**: the server turns the recipient's existing `deliver_ack` into a `receipt` frame for the sender. The receiving client needs no change; old clients ignore the new frame. | Like real chat apps; the smallest protocol change. Existing scenarios gain `READ` lines. | Human, on AI recommendation, 2026-10-12 | in force |
| D38 | Receipts are stored and delivered like messages (mailbox, `seq` order, removed on `deliver_ack`); at most one per message; none for a message to yourself. | A receipt reaches an offline or restarted sender, consistent with the outbox's "never lost". | AI default, pending confirmation | in force |
| D39 | Output: `READ id=<msg_id> seq=<msg_seq> by=<by>` (machine) and `[read]   by <by> (#<msg_seq>)` (friendly, aligned with `[sent]`); duplicates are suppressed by a seen-receipts set kept in memory. | Same shape as the existing lines. | AI default, pending confirmation | in force |
