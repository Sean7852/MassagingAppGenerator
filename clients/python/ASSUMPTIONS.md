# Assumptions (python client)

Choices the spec left open that are not visible outside the client.

- Module layout: `msgclient/cli.py` (argument and command parsing), `output.py` (escaping and
  line formatting, the only stdout writer), `storage.py` (state file), `protocol.py` (frame
  encoding and validation), `client.py` (state machine and event loop).
- One `asyncio.Queue` holds every event: stdin lines (from the daemon thread), frames and
  "closed" events (from one reader task per connection). Each event carries its connection
  object, so events from old connections can be told apart and ignored.
- Commands that arrive while going online go into a separate deque and are handled first
  afterwards, in order.
- Closing a connection on purpose (`/offline`, rejected login) runs as a background task so the
  event loop is not held up by the close handshake. On `/quit` the close is awaited.
- The state file is written with `json.dumps(..., ensure_ascii=False)` and then `f.write`,
  instead of `json.dump`. The bytes on disk are the same.
- `main.py` returns the exit code from `main()` and then calls `os._exit(code)` after flushing
  stdout and stderr. This stops the interpreter shutdown from getting stuck on the stdin lock,
  which the daemon reader thread may still hold.
- If a frame or the state contains a lone surrogate, so that it cannot be encoded as UTF-8,
  it is written as JSON with `ensure_ascii=True` instead. Our own clients never produce this.
- The usage message on stderr reads `usage: python main.py [--server <url>] [--data-dir <dir>] [--machine]`.
- *Pending confirmation* (only visible with malformed server input): a lone surrogate in a
  value that is written unchanged (`<from>`, `<id>`, `<by>`, `<name>`, `<code>`, `<ref>`)
  cannot be written as UTF-8, so it is written as U+FFFD, the same as in `<text>`.
