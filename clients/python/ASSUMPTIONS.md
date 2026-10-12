# Assumptions (python client)

Choices the spec left open that are not visible outside this client.

- Module layout: `msgclient/cli.py` (argument and command parsing), `output.py` (escaping and
  line formatting, the single stdout writer), `storage.py` (state file load/validate/save),
  `frames.py` (JSON encode/decode and per-type frame validation), `client.py` (state machine,
  event loop, `main`).
- All events (stdin lines, end of input, frames, connection closed) go through one
  `asyncio.Queue`. While going online, stdin events taken from the queue are kept in a
  `deque` that is drained before the queue is read again.
- A connection the client closes on purpose (`/offline`, rejected login) is closed in a
  background task; on `/quit` the close is awaited (bounded by `close_timeout=1`) before returning.
- A failure to send a frame on a closing connection is ignored; the connection's "closed"
  event that follows does the handling.
- An exception from `sys.stdin.readline()` is reported on stderr and treated as end of input.
- The stderr usage message and the stderr texts for load/save failures are free-form.
