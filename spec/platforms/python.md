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
3. **stdin encoding and line endings**: at startup call
   `sys.stdin.reconfigure(encoding="utf-8", errors="replace", newline=None)`. `newline=None`
   (universal newlines) ends a line at `\r\n`, `\n` or `\r` on **every** OS; without it, Python
   on Linux and macOS splits only at `\n`. `errors="replace"` turns invalid bytes into U+FFFD.
   `readline()` then returns the line ending in a single `"\n"`, or with no ending for a last
   unterminated line; strip the `"\n"` if present.
4. **Output** goes through one function that writes the line plus `"\n"` and calls
   `sys.stdout.flush()`. At startup call `sys.stdout.reconfigure(encoding="utf-8", newline="\n")`.
   Nothing else writes to stdout (no `print` for logs; use stderr). Before printing a received
   text or server message, replace lone surrogates with U+FFFD
   (`re.sub("[\ud800-\udfff]", "�", s)`); `json.loads` turns valid pairs into one character,
   so anything left in that range is lone.
5. **Connecting**: `connect(url, open_timeout=5, ping_interval=20, ping_timeout=20,
   close_timeout=1, max_size=64 * 1024, proxy=None)`. `ping_interval` and `ping_timeout`
   implement the keep-alive of 20-client.md; `proxy=None` stops the library from using proxy
   settings from the environment. Treat any exception from opening the connection (including
   `OSError`, `TimeoutError`, `InvalidURI`, `InvalidHandshake`) as `connect_failed`.
6. **Receiving**: one task reads frames from the connection and feeds the same event-handling
   path as stdin commands, so events are handled one at a time. Binary messages (`bytes`) are
   ignored.
7. **Going online holds commands up**: while going online, stdin lines that arrive are kept
   aside and handled afterwards, in order; only connection events are handled meanwhile.
8. **Arguments**: parse `sys.argv[1:]` by hand, following the grammar in 30-cli.md exactly. Do
   not use `argparse`: it accepts `-h`, shortened options and repeated options, which the spec
   forbids. On an error write a usage message to stderr and exit with status 2.
9. **Saving** ([40-storage.md](../core/40-storage.md)): `pathlib.Path.mkdir(parents=True,
   exist_ok=True)`, write `state.json.tmp` with `json.dump(..., ensure_ascii=False)` and
   `encoding="utf-8"`, flush and `os.fsync`, then `os.replace` onto `state.json` (atomic on
   Windows too). Saving is synchronous, inside the event handler, before the output line.
   When validating a loaded file, remember that `True` is an `int` in Python: check
   `type(v) is int` (or a float with a whole value) for `version`.
10. **Exit**: after `BYE`, close the connection and return from `main`; the exit status is 0.
    The stdin thread is a daemon, so it does not keep the process alive. To exit with status 1
    in the middle of a run (saving failed), write the message to stderr, flush stdout and
    stderr, then call `os._exit(1)`.

## Tests
`tests/` contains `unittest` tests that need no server and no network, covering at least:
stdin command parsing (every row of the command table and the examples in 30-cli.md, and a
text containing U+2028), argument parsing (each error case in 30-cli.md § Invocation), output
escaping in both modes (including a lone surrogate), and state-file validation (each rule in
40-storage.md).
