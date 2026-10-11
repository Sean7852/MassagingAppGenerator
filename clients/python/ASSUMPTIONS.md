# Assumptions (python client)

- Module layout: `msgclient/commands.py` (line parsing), `msgclient/output.py` (escaping, line
  formats, the single stdout writer), `msgclient/client.py` (state machine, connection, stdin
  thread), `msgclient/cli.py` (argparse + `asyncio.run`).
- All events (stdin lines, end of input, connection opened/failed, frames, close) go through one
  `asyncio.Queue` and are handled one at a time by one loop. Opening the connection runs in a
  task that posts its result to that queue, so commands keep being handled while `connecting`.
- Events from a connection the client already closed (e.g. after a rejected login) are told
  apart by object identity and dropped.
- `argparse` is created with `add_help=False` and `allow_abbrev=False`, so `-h` and abbreviations
  such as `--serv` count as "any other argument" (stderr, exit 2). `--server=<url>` is accepted
  as the same argument.
- A frame of a known `type` whose required fields are missing or have the wrong JSON type (for
  example a non-integer `seq`) is treated as invalid server input and ignored (90-defaults rule 2).
  An `error` `ref` that is not a string is treated as absent. A conforming server never sends these.
- `deliver` and `ack` frames that arrive while `connecting` are ignored (a conforming server
  sends none before `login_ok`).
- A failed `send` on the socket is only logged to stderr; the reader task's close event does the
  `not_sent` / `DISCONNECTED` reporting.
- On `/quit` while `connecting`, the connect task is cancelled (or, if it already opened, the
  connection is closed).
- Diagnostics (connect failures, connection errors, unexpected exceptions) go to stderr.
