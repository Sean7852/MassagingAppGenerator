# Assumptions (typescript client)

Choices the spec left open, all invisible outside this client.

- Module layout: `args.ts` (argument parsing), `commands.ts` (command-line parsing), `lines.ts`
  (stdin line splitting), `output.ts` (escaping and line formatting, the single stdout writer),
  `storage.ts` (state-file validation, load, atomic save), `frames.ts` (server-frame
  validation), `client.ts` (state machine and event queue), `main.ts` (wiring).
- Arguments are parsed by hand, not with `node:util` `parseArgs`.
- stdin is split into lines by a small splitter of our own (`lines.ts`) over
  `process.stdin.setEncoding("utf8")`, not by `node:readline`. On Node 24 readline also ends a
  line at U+2028 and U+2029, which breaks 30-cli.md (U+2028 is part of the text). This
  departs from platform rule 1 to keep the core behavior. The rule should be updated.
- After `BYE`, stdin is destroyed (not just paused). On Windows a paused stdin pipe keeps the
  process alive.
- The 5-second connect limit is enforced by `handshakeTimeout: 5000` plus our own 5 s timer.
  Whichever fires first counts as `connect_failed`.
- When the client closes a connection itself, it uses `ws.terminate()` if the handshake has
  not finished and `ws.close()` otherwise.
- The seen set is keyed by `JSON.stringify([from, id])`.
- `seq` is valid when `Number.isInteger(seq)` and `1 <= seq <= Number.MAX_SAFE_INTEGER`.
- The stderr texts (usage message, load/save errors, internal errors) are our own wording.
