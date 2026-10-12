# Assumptions (TypeScript client)

Choices the spec left open that are invisible outside this client.

- Module layout: `args.ts` (argument parsing), `commands.ts` (command parsing and the stdin
  line splitter), `output.ts` (escaping and line formatting), `frames.ts` (server frame
  validation), `storage.ts` (state file load/validate/save), `client.ts` (state machine, event
  queue, connection handling), `main.ts` (wiring).
- Arguments are parsed by hand rather than with `node:util` `parseArgs`. For
  `--server <value>` / `--data-dir <value>` the next argument is taken as the value whatever it
  looks like.
- `tsconfig.json` adds `"lib": ["ES2023", "ES2024.String"]` so `String.prototype.toWellFormed`
  type-checks with target ES2023; also `"types": ["node"]` and `"skipLibCheck": true`.
- The 5 s connect limit is enforced both by `ws`'s `handshakeTimeout` and by a 5 s timer of the
  client's own; whichever fires first counts as `connect_failed`.
- Closing a connection on purpose (`/offline`, rejected login, `/quit`) calls `ws.close()` and,
  if the close handshake has not finished after 1 s, `ws.terminate()` (an unref'd timer, so it
  never keeps the process alive by itself).
- A pong timeout timer is started at a ping only if none is already running; any pong clears it.
- Seen sets are keyed by `JSON.stringify([from, id])` (and `[by, msg_id]` for receipts).
- Unexpected internal failures (including `uncaughtException` / `unhandledRejection`) are
  written to stderr with `console.error`, and the client keeps running.
- The usage message on stderr is `usage: main [--server <url>] [--data-dir <dir>] [--machine]`,
  preceded by a line naming the problem.
- After `BYE` (or a failed save) stdin listeners are removed and stdin is destroyed so the
  process can end on its own.
