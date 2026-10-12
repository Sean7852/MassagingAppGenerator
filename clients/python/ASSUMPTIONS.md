# Assumptions (python client)

Choices the spec left open that are invisible outside this client.

- Module layout: `msgclient/args.py` (arguments), `commands.py` (stdin line parsing),
  `output.py` (escaping, the single stdout writer, machine/friendly formatting),
  `frames.py` (decoding/checking server frames, compact JSON encoding), `storage.py`
  (state file load/validate/save), `client.py` (state machine and event loop).
- One `asyncio.Queue` carries stdin lines, end of input, frames and "connection closed"
  events; each frame/close event is tagged with its connection object so events from old
  connections can be recognised and ignored.
- Lines typed while going online are kept in a deque and handled, in order, right after going
  online finishes, before any later queued event.
- One reader task per connection; `websockets` handles ping/pong (keep-alive) and its
  closing on pong timeout surfaces as the normal "connection closed" event.
- When the client closes a connection itself (`/offline`, rejected login, `/quit`) it drops the
  reference first and then awaits `close()` (bounded by `close_timeout=1`).
- Diagnostics (connect failure reason, internal errors with traceback, load/save errors) go to
  stderr; the stderr wording is free text.
- State-file loading: a missing file, or a data directory path that is not a directory
  (`FileNotFoundError` / `NotADirectoryError`), counts as "no file"; any other read error is
  "cannot be read". `NaN`/`Infinity` literals are rejected as not JSON.
- State-file validation treats a string containing a lone surrogate (from a `\ud800`-style JSON
  escape) as not a valid string, since it cannot be encoded as UTF-8.
- The stdout writer replaces lone surrogates with U+FFFD in the whole line (not only in text
  and message) so that writing UTF-8 can never fail; with valid server input only text and
  message can contain them.
- The state file is written with `newline="\n"` and without indentation.
