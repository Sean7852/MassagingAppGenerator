# Open questions

The generator refuses to run while the **Blocking** section has an unchecked item (`- [ ]`).
Resolve a question by changing the spec, recording the decision in `decisions/`, and then
checking the item (`- [x]`) or deleting it.

## Blocking

Review of spec version 2, 2026-10-11. Each item: question, where, options, recommendation.
All B items were decided by the human on 2026-10-12: see D21–D32 in
[decisions/README.md](decisions/README.md). Checked N items are applied as D34.

- [x] **B1. Commands during a `/login` attempt (state `connecting`, no saved name).**
  Where: `core/20-client.md` § `/login`, § `/send`, § `/offline`; `core/40-storage.md` § The state file.
  `/login` only maps "becomes `offline`" to `idle` *inside the going-online steps*. So:
  (a) `/offline` during a `/login` attempt says "set the state to `offline`, print `OFFLINE`",
  which leaves an `offline` state with no saved name. That breaks the state table, and later
  `/online` would go online with no name.
  (b) `/send` during a `/login` attempt is not `idle`, so it is queued and **saved** with
  `name: null`. If the login is then rejected, the client is `idle` with a non-empty outbox
  on disk, which contradicts "nothing is saved". A later `/login bob` would send those
  messages as `bob`.
  Options: (1) treat "no saved name" as `idle` for every command, so `/send` prints
  `not_logged_in` and `/offline` returns to `idle` (prints `OFFLINE`? or nothing?) until
  `login_ok`; (2) allow queueing, and on a rejected login keep the outbox (state which name
  it belongs to) or discard it; (3) add a separate state `logging_in` with its own row for
  every command.
  Recommendation: (1). `/send` → `ERROR not_logged_in`; `/offline` → abandon the attempt,
  print `OFFLINE`, state `idle`, nothing saved. Also say that a file with `name: null` and a
  non-empty outbox is invalid (see B10). Add a scenario.

- [x] **B2. Is opening a connection one blocking event, or asynchronous?**
  Where: `core/20-client.md` § Going online, § Concurrency ("each to completion").
  If a client handles `/online` by waiting for the connection to open (up to the 5 s
  timeout) before it handles the next event, a `/send` typed in the meantime prints
  `ERROR connect_failed` **then** `QUEUED`. A client that opens the connection
  asynchronously prints `QUEUED` **then** `ERROR connect_failed`. Also, `/offline` "abandons
  the attempt", but a blocking client cannot do that. The same applies to the automatic
  online at startup.
  Options: (1) opening is asynchronous: the command's handling ends once the attempt has
  started; "opened", "failed" and "closed" are later events in the same single queue;
  (2) opening is part of handling the command, and other events wait for it.
  Recommendation: (1). Say it explicitly in § Concurrency and add a scenario where `/send`
  and `/offline` are typed while connecting to a server that does not answer the handshake.

- [x] **B3. Frames received in states other than `online`, and frames from an old connection.**
  Where: `core/20-client.md` § Receiving ("while `online`"), § Other frames, § `/offline`.
  The spec defines `deliver` and `error` only "while `online`", and `login_ok`/`error` while
  `connecting`. It does not say what happens to: an `ack`, `deliver` or `error` that was
  already received (or queued for handling) when `/offline` or `/quit` was processed; a
  `deliver`/`ack` that arrives while `connecting` before `login_ok`; or frames or close events
  of a previous connection that are handled after a new connection was opened (`/offline`
  then `/online` quickly). Two clients could print or skip an `ERROR`/`RECV`, send a
  `deliver_ack`, or print a stray `DISCONNECTED` for the old connection.
  Options: (1) every frame and close event belongs to one connection; events from a
  connection that is not the current one are ignored, and in `idle`/`offline` every frame is
  ignored; (2) handle buffered frames from a closed connection as if still online.
  Recommendation: (1), plus "in `connecting`, any frame other than `login_ok` and `error` is
  ignored".

- [x] **B4. Known frame types with missing, null or wrong-typed fields.**
  Where: `core/10-protocol.md` § Frames: server → client; `core/90-defaults.md` rule 2 (covers
  only unknown types and fields, and invalid JSON).
  Examples: `deliver` without `text`, or with `seq` as a string, `1.0`, `0` or > 2^53; `ack`
  without `seq`; `error` with `"ref": null`, or without `message`; `login_ok` without `name`.
  A dynamic implementation prints `seq=undefined`/`ref=null`, while another raises and
  reports on stderr. `1.0` prints as `1.0` in one language and `1` in the other. Large integers
  lose precision in one language.
  Options: (1) a known frame with a required field missing or of the wrong JSON type is
  ignored entirely (no output, no `deliver_ack`, no state change); `ref: null` counts as
  absent; integers must be JSON integers in 1..2^53−1; (2) print what can be printed.
  Recommendation: (1), as a new rule in 90-defaults.md or 10-protocol.md.

- [x] **B5. Characters in received text that cannot be written as UTF-8 (lone surrogates).**
  Where: `core/30-cli.md` § Output, § Escaping.
  Another user's raw WebSocket client can send `"text":"\ud800"`. The server accepts it and
  delivers it as a JSON escape. A strict UTF-8 writer fails, so no `RECV` line is printed and
  the error goes to stderr. A lenient writer prints U+FFFD. The same applies to an error's
  `message`.
  Options: (1) replace each lone surrogate with U+FFFD; (2) escape it as `\uXXXX` (this would
  be a new escape); (3) treat such a frame as malformed and ignore it (see B4).
  Recommendation: (1). Add a unit-test note to both platform modules.

- [x] **B6. Regex dialect of the command table.**
  Where: `core/30-cli.md` § Input (`^/send ([^ ]+) (.+)$`); `README.md` § Normative words
  ("regex … is exact").
  In JavaScript, `.` without the `s` flag does not match U+2028, U+2029 or `\r`. In Python,
  `.` matches all of these except `\n`. So `/send bob a<U+2028>b` is a send in one client and
  a usage error in the other. Python's `$` also matches before a final `\n`.
  Options: (1) define the table in words: "`/send`, one space, a name of one or more
  non-space characters, one space, then a text of one or more characters of any kind";
  (2) keep the regexes and say "`.` matches any character; `$` is the end of the line".
  Recommendation: (1), with (2) as a note for implementers. Add a unit-test row with U+2028.

- [x] **B7. Invalid UTF-8 on stdin.**
  Where: `core/30-cli.md` § Input ("UTF-8 text"); `platforms/python.md` rule 3;
  `platforms/typescript.md` rule 1.
  With strict decoding (the Python rule as written), an invalid byte raises inside the stdin
  thread. That thread then dies, and the client never sees later lines or end of input. Node
  replaces the byte with U+FFFD and carries on. A leading BOM is also unspecified.
  Options: (1) invalid bytes decode to U+FFFD and the line is handled normally; a BOM is kept
  as a character; (2) a line with invalid UTF-8 is an `unknown_command`; (3) undefined (out of
  scope).
  Recommendation: (1) (`errors="replace"` in Python). Say it in 30-cli.md.

- [x] **B8. The Python platform rule for stdin line endings is wrong outside Windows.**
  Where: `platforms/python.md` rule 3 ("keeping the default universal newlines").
  As far as I know, CPython opens `sys.stdin` with `newline="\n"` on POSIX (universal
  newlines only on Windows), and `reconfigure(encoding=…)` keeps that. On Linux or macOS, a
  lone `\r` would not end a line and `\r\n` would leave a `\r` in the command. That contradicts
  `30-cli.md` § Input and scenario `05_text_fidelity`, and the TypeScript client would behave
  differently. Please verify this before deciding.
  Options: (1) require `sys.stdin.reconfigure(encoding="utf-8", errors=…, newline=None)`
  explicitly; (2) read raw bytes and split lines in client code per 30-cli.md.
  Recommendation: (1), plus a platform unit test that feeds `a\rb\r\nc\n`.

- [x] **B9. Command-line argument details.**
  Where: `core/30-cli.md` § Invocation; `platforms/python.md` rule 8; `platforms/typescript.md`
  rule 7.
  `argparse` (as the platform rule says to use it) accepts `-h`/`--help`, which prints help to
  **stdout** and exits **0**. It also accepts abbreviations (`--serv`, `--data`).
  `parseArgs` does neither. Also unspecified: `--server=url` form, a repeated option (last wins
  or error?), an empty value, `--`, and which comes first when both the arguments and the
  saved state are bad (exit 2 or 1).
  Options: (1) exact grammar: only `--server <v>`, `--server=<v>`, `--data-dir <v>`,
  `--data-dir=<v>`, each at most once; anything else (including `-h`, abbreviations, repeats,
  positionals) → usage on stderr, exit 2; arguments are checked before the state is loaded;
  (2) allow the library defaults per platform and declare them unspecified.
  Recommendation: (1). Platform modules then say `allow_abbrev=False, add_help=False` for
  Python and `strict: true` for TS. Add a conformance or harness check for exit status 2.

- [x] **B10. Exactly what makes `state.json` "valid".**
  Where: `core/40-storage.md` § The state file, § Loading.
  Unspecified: `version` given as `1.0` (indistinguishable from `1` in JavaScript, a float in
  Python) or `true` (equal to `1` in Python); a missing `outbox` or `name`; `name` as `""`;
  outbox entries with non-string fields, extra fields, a non-UUID or uppercase `id`, duplicate
  ids, or empty `text`; `name: null` with a non-empty outbox (see B1); a UTF-8 BOM. One client
  exits 1 and another goes online. An outbox `id` that is not a lowercase UUID also stalls the
  outbox forever: the server answers that `send` with `bad_request` **without** `ref`
  (server.py `on_send`), so the message stays in flight and nothing after it is ever sent.
  Options: (1) strict: an object with exactly-typed `version` (JSON integer 1), `name` (string
  or null), `outbox` (array of objects with string `id` matching the lowercase-UUID regex,
  string `to`, string `text`); `name: null` requires an empty outbox; anything else → exit 1;
  (2) lenient with listed coercions.
  Recommendation: (1). Give the exact UUID regex in the spec. Ignore extra fields at both
  levels. Add harness tests with bad files.

- [x] **B11. A `/send` whose frame would exceed 64 KiB.**
  Where: `core/10-protocol.md` § Transport ("at most 64 KiB"); `core/20-client.md` § `/send`.
  The client does not limit the text length, and a long stdin line is possible. The server
  closes the connection (WebSocket 1009), the client prints `DISCONNECTED`, the message stays
  first in the outbox, and every later `/online` disconnects again: the outbox is blocked for
  good. A careful implementer might instead reject it locally because of the protocol's
  "at most", so the two clients would differ.
  Options: (1) the client refuses at `/send` when the encoded frame would exceed 64 KiB, with a
  new local error (for example `ERROR code=too_long message=…`), and nothing is queued;
  (2) the client refuses texts over 4096 characters itself (but "only the server checks"
  would then need a change); (3) keep it as is and accept the stuck outbox.
  Recommendation: (1). Define the exact code and message and how the size is measured (bytes
  of compact JSON in UTF-8), and add a scenario.

- [x] **B12. Connection library defaults that change observable behavior.**
  Where: `platforms/python.md` rule 5; `platforms/typescript.md` rule 4; `core/90-defaults.md`
  rule 1 ("no … timeouts … the spec does not ask for").
  `websockets` 15 `connect()` sends keepalive pings by default (`ping_interval=20`,
  `ping_timeout=20`). Against a stalled server, the Python client prints `DISCONNECTED` after
  about 40 s, while `ws` never pings and stays `online`. `websockets` 15 also uses HTTP proxies
  from environment variables and follows redirects by default; `ws` does neither. These are
  observable differences that the platform modules introduce.
  Options: (1) the core says "no keepalive pings, no proxies, no redirects", and the platform
  modules pin `ping_interval=None, proxy=None` (and no redirects) for Python; (2) the core
  defines a keepalive (interval and timeout) that both must implement.
  Recommendation: (1), consistent with defaults rule 1.

- [x] **B13. Signals and broken stdout.**
  Where: `core/30-cli.md` § Invocation (exit statuses); `core/90-defaults.md` rule 3.
  Ctrl+C or SIGTERM: Python raises `KeyboardInterrupt` (traceback, exit status 1 or −2),
  while Node exits with 130/143. Does either print `BYE`? A closed stdout (EPIPE) is also
  unspecified.
  Options: (1) SIGINT/SIGTERM behave like end of input (`BYE`, exit 0); (2) exit at once with
  no stdout output and an unspecified status (out of scope, never tested); (3) fixed status
  130.
  Recommendation: (2), written down explicitly as out of scope, so that neither generator
  invents behavior. Choose (1) if the human wants Ctrl+C to be clean.

## Non-blocking

- [ ] Should `login` carry a protocol version so the server can refuse clients built from an
  older spec? Not needed while all clients come from the same spec version. Revisit when the
  first extension changes frames.

- [x] **N1. What counts as "opened", and the open timeout, belong in core.**
  Where: `core/20-client.md` § Going online steps 2 and 6; `platforms/*.md` (5 s timeouts,
  "`error` or `close` before `open`").
  The boundary between `connect_failed` and `DISCONNECTED` (WebSocket handshake complete)
  and the 5 s timeout are observable, but only the platform modules state them. Today both
  agree. Recommendation: move both to 20-client.md ("opened = WebSocket handshake
  completed; an attempt that has not opened within 5 s fails") and make the platform modules
  refer to it.

- [x] **N2. Durability differs: Python must `fsync`, TypeScript does not.**
  Where: `platforms/python.md` rule 9; `platforms/typescript.md` rule 8; `core/40-storage.md`
  § Saving ("a crash at any moment").
  A killed process is safe either way. After a power loss, the TS client may be left with an
  empty or old file. Options: require `fsyncSync` in TS too, or soften the core wording to
  "process crash". Recommendation: require fsync in both.

- [x] **N3. Unknown fields in `state.json`: kept or dropped on the next save?**
  Where: `core/40-storage.md` § Loading ("Unknown extra fields are ignored").
  This matters for a future format version and for interop between clients. Recommendation:
  dropped (simplest), stated explicitly.

- [x] **N4. Say explicitly that fields other than `<text>`/`<message>` are written raw.**
  Where: `core/30-cli.md` § Output, § Escaping.
  `to` is user-typed and can contain `\` or a tab (`QUEUED … to=a\tb` with a real tab).
  An implementer might escape every field. The current wording implies raw, but saying so
  avoids a guess. Recommendation: add "all other values are written unchanged".

- [ ] **N5. `login_ok` with a `name` that differs from the saved name (on `/online` or at
  startup).** Where: `core/20-client.md` § Going online step 4.
  `/login` saves the frame's name, but going online again does not say whether to update the
  saved name. The server always echoes the name, so this cannot be observed today.
  Recommendation: print the frame's name and do not save.

- [x] **N6. `deliver` whose `to` is not the client's name; binary WebSocket frames.**
  Where: `core/20-client.md` § Receiving; `core/10-protocol.md` § Transport.
  Implied: show it anyway; binary frames are not specified (Python's `json.loads` accepts
  bytes). The server never produces either. Recommendation: `to` is not checked; binary
  frames are ignored.

- [x] **N7. How to exit at runtime, and how long exiting may take.**
  Where: `platforms/typescript.md` rule 9 (covers only bad state at **startup**);
  `core/40-storage.md` § Saving (exit 1 on save failure); `core/20-client.md` § `/quit`.
  In TS, setting `process.exitCode = 1` mid-run does not end the process while stdin and the
  socket are open. In Python, `ws.close()` can wait up to `close_timeout` (10 s) against an
  unresponsive server, while the runner allows 5 s after `BYE`. Recommendation: the platform
  modules say how to stop immediately (TS: close stdin, the socket and timers, or
  `process.exit` after draining stdout; Python: `close_timeout` ≤ 1 s, or don't wait for the
  close handshake on `/quit`).

- [x] **N8. A saved name that the server rejects leaves the user stuck.** (Resolved by v4: the name is no longer saved, D40.)
  Where: `core/20-client.md` § Startup and § `/login`; `core/40-storage.md`.
  This only happens with a hand-edited file. Every `/online` fails, and `/login` is refused.
  The only way out is deleting the file. This is acceptable given "no logout", but worth
  documenting.

- [ ] **N9. Two processes on one data directory.**
  Where: `core/40-storage.md` § Data directory ("must use different").
  The behavior is undefined (last writer wins, lost outbox entries). Options: a lock file and
  exit 1, or leave it as a documented misuse. Recommendation: leave it as is for v2 and
  document it.

- [x] **N10. README says extensions are "none in v1" and `spec/extensions/` does not exist.**
  Where: `README.md` § Layers. Recommendation: update to "none in v2" and create the empty
  folder (or say it may be absent), so generators don't stop on a missing input.

- [ ] **N11. Rules not covered by any conformance scenario.**
  Where: `conformance/scenarios/*`. No scenario contradicts the prose. These rules have no
  scenario:
  `/send`, `/online`, `/login` and `/offline` while `connecting` (B1, B2);
  `DISCONNECTED` while `connecting` (close before `login_ok`); `connect_failed` at startup
  with a saved name; resending an in-flight message after `/offline`/disconnect (same `id`,
  one `SENT`, one `RECV`); the seen set suppressing a redelivered message; text over 4096
  characters (`bad_request` with `ref`, removed from outbox); escaping of received `\n`/`\r`
  (needs a raw sender); unknown frame types and fields; exit status 2 (bad arguments) and 1
  (bad or unwritable state file); the `state.json` format itself, including one platform
  reading a data directory written by the other; a crash while a message is in flight; a
  leftover `state.json.tmp`; nothing printed after `BYE` while frames are still arriving.
  Recommendation: add scenarios where the runner can drive them. The rest need a fake-server
  or file-inspection step in the runner, or harness tests.
