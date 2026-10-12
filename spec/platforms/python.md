---
# Read by the harness (harness/platforms.py). Commands run with clients/python/ as the working
# directory. A leading `python` means the Python running the harness.
platform: python
short: py
dir: clients/python
sources: ".py"        # files that must carry the generated-file header
ignore: [__pycache__]  # build output, never checked or hashed
setup:
  - python -m pip install -q --disable-pip-version-check -r requirements.txt
build:
  - python -m compileall -q main.py msgclient tests
test:
  - python -m unittest discover -s tests -t . -q
run: python main.py
---

# Platform — Python

How to build the client in Python. Behavior comes only from `spec/core` and `spec/extensions`;
nothing here may change what the client prints or sends.

## Runtime and libraries
- Python **3.13**. Standard library plus exactly one package: `websockets` (`>=15,<16`),
  using its asyncio API (`websockets.asyncio.client.connect`).
- `requirements.txt` in the client folder lists only `websockets>=15,<16`.
- Message ids: `str(uuid.uuid4())` (already lowercase).
- JSON: `json.dumps(frame, separators=(",", ":"), ensure_ascii=False)`.

## Layout
```
clients/python/
  main.py              entry point: parses arguments, runs the client
  msgclient/           the client package (module split is up to the generator)
    __init__.py
  tests/               unittest tests, run by the test command above
    __init__.py
  requirements.txt
```
- `main.py` must work when started as `python main.py` from inside `clients/python/`.
- Every `.py` file starts with the generated-file header (see the generator rules).

## Must-follow implementation rules
These avoid known platform pitfalls. They do not change behavior.
1. **One asyncio event loop** runs everything (`asyncio.run`).
2. **stdin is read by a background daemon thread** that calls `sys.stdin.readline()` in a loop
   and hands each line to the event loop with `loop.call_soon_threadsafe` (for example onto an
   `asyncio.Queue`). End of input (`""`) is handed over as a sentinel. Do not use
   `loop.add_reader` or `connect_read_pipe` on stdin: they do not work on Windows.
3. **Encoding**: at startup call `sys.stdin.reconfigure(encoding="utf-8")`, keeping the
   default universal newlines, which end a line at `\r\n`, `\n` or `\r` as the CLI spec says
   (`readline()` then returns the line ending in a single `"\n"`, or with no ending for a last
   unterminated line; strip the `"\n"` if present). Also call
   `sys.stdout.reconfigure(encoding="utf-8", newline="\n")`, so Windows pipes use UTF-8 and
   output uses LF only.
4. **Output** goes through one function that writes the line plus `"\n"` and calls
   `sys.stdout.flush()`. Nothing else writes to stdout (no `print` for logs; use stderr).
5. **Connecting**: `connect(url, open_timeout=5, max_size=64 * 1024)`. Treat any exception from
   opening the connection (including `OSError`, `TimeoutError`, `InvalidURI`,
   `InvalidHandshake`) as `connect_failed`.
6. **Receiving**: one task reads frames from the connection and feeds the same event-handling
   path as stdin commands, so events are handled one at a time.
7. **Exit**: after `BYE`, close the connection and return from `main`; the exit status is 0.
   The stdin thread is a daemon, so it does not keep the process alive.
8. Argument parsing with `argparse`; it already exits with status 2 and writes to stderr on
   bad arguments.
9. **Saving** ([40-storage.md](../core/40-storage.md)): `pathlib.Path.mkdir(parents=True,
   exist_ok=True)`, write `state.json.tmp` with `json.dump(..., ensure_ascii=False)` and
   `encoding="utf-8"`, flush and `os.fsync`, then `os.replace` onto `state.json` (atomic on
   Windows too). Saving is synchronous, inside the event handler, before the output line.

## Tests
`tests/` contains `unittest` tests that need no server and no network, covering at least:
stdin command parsing (every row of the parsing table in 30-cli.md) and output escaping.
