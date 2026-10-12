# Assumptions (typescript client)

- Module layout: `src/main.ts` (arguments, stdin, `ws` wiring, event loop), `src/client.ts`
  (state machine, behind a small `Conn`/`Connector` interface so it can be unit-tested without a
  network), `src/commands.ts` (line parsing), `src/output.ts` (line formats, escaping, the single
  stdout writer).
- The parsing regexes use the JS `s` (dotAll) flag so `.` in `^/send ([^ ]+) (.+)$` matches any
  character, including U+2028/U+2029, which JS `.` would otherwise exclude.
- The seen set key is `JSON.stringify([from, id])`.
- Server frames with a known `type` whose required fields are missing or of the wrong type
  (for example, a non-integer `seq`) are treated as invalid input and ignored (90-defaults rule 2).
  An `error` frame whose `ref` is not a string is treated as having no `ref`.
- Binary WebSocket messages are ignored, since the protocol only uses text frames.
- `parseArgs` accepts `--server=<url>` as well as `--server <url>`. If `--server` is given more
  than once, the last value wins. The usage text on stderr is `usage: node dist/main.js [--server <url>]`.
- A WebSocket `error` after `open` is only logged to stderr; the `close` event that follows it
  does the disconnection handling.
- Events from a connection the client has already closed or replaced are ignored. These are told
  apart by object identity.
- After `BYE`, the event loop stops, the readline interface is closed and stdin is paused, so the
  process exits on its own once the WebSocket close finishes.
- `tsconfig.json` also sets `"types": ["node"]` and `"skipLibCheck": true`.
