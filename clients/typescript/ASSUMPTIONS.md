# Assumptions (typescript client)

Choices the spec left open that are invisible outside this client:

- Module layout: `args.ts` (argument parsing), `commands.ts` (command table and stdin line
  splitter), `output.ts` (escaping, machine/friendly formatting, the single stdout writer),
  `storage.ts` (state-file validation, load, atomic save), `frames.ts` (server-frame
  validation), `client.ts` (state machine and the single event queue), `main.ts` (wiring).
- Going online uses an own 5 s timer in addition to `ws`'s `handshakeTimeout`; whichever fires
  first ends the attempt as `connect_failed`.
- A connection the client closes on purpose (`/offline`, rejected login, `/quit`) uses
  `ws.close()`; an unref'd 2 s timer then calls `ws.terminate()` so a dead peer cannot keep the
  process alive. An attempt that never opened is closed with `ws.terminate()`.
- Keep-alive keeps at most one pong deadline at a time: it is set by a ping when none is
  pending and cleared by any `pong`.
- Seen sets key on `JSON.stringify([from, id])` (and `[by, msg_id]` for receipts).
- `--server`/`--data-dir` followed by another argument take that argument as the value, even
  if it starts with `--` (the grammar says the value is "the next argument").
- Usage text on stderr: `usage: node dist/main.js [--server <url>] [--data-dir <dir>] [--machine]`
  preceded by a one-line reason; load/save failures print a one-line reason on stderr.
- Unexpected exceptions in a handler, and uncaught exceptions/rejections, are logged with
  `console.error` and the client keeps running.
