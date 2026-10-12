# 30 — CLI contract

Everything observable about a client from outside the process. Conformance tests compare this
output byte for byte, so every client MUST produce exactly these lines.

## Invocation

```
<platform run command> [--server <url>] [--data-dir <dir>]
```
- `--server <url>`: WebSocket URL of the server. Default `ws://127.0.0.1:8765`.
- `--data-dir <dir>`: where the name and outbox are saved ([40-storage.md](40-storage.md)).
  Default `.msgdata`, relative to the current working directory.
- Any other argument: print a usage message to **stderr** and exit with status 2.
- At startup the client loads its saved state. With no saved name it prints nothing until the
  first command. With a saved name it goes online by itself ([20-client.md](20-client.md#startup)).

Exit status: 0 after `BYE`; 2 for bad arguments; 1 when the saved state cannot be loaded or
saved ([40-storage.md](40-storage.md)), with a message on stderr.

## Input (stdin)

- UTF-8 text, one command per line. A line ends at `\r\n`, `\n`, or a lone `\r`; the line
  ending is removed and nothing else is trimmed. So `\r` can never be part of a command.
  A last line with no line ending before end of input is still a line.
- An empty line is ignored (no output).
- A line is parsed by these rules, first match wins:

| Line | Command |
|---|---|
| matches `^/login ([^ ]+)$` | login with that name |
| matches `^/send ([^ ]+) (.+)$` | send group 2 (the text, kept exactly, spaces included) to group 1 |
| is exactly `/online` | go online |
| is exactly `/offline` | go offline |
| is exactly `/quit` | quit |
| starts with `/login`, `/send`, `/online`, `/offline` or `/quit` followed by a space or end of line | usage error |
| anything else | unknown command |

So `/send bob  hi` sends the text ` hi` (with a leading space) to `bob`, and `/sendx` is an
unknown command. Names are not checked by the client ([10-protocol.md](10-protocol.md#names)).

- End of input (stdin closed) behaves like `/quit`.

## Output (stdout)

- UTF-8, one event per line, each line ending with `\n` only (never `\r\n`), written and
  flushed as soon as the event happens.
- Only the lines below are ever written to stdout. No prompts, banners, colors or logging.
  Diagnostics MAY go to stderr, which is never compared.
- Fields are separated by one space. The order of fields is exactly as shown.
- `<text>` and `<message>` values are **escaped** (see below) and always come last, because
  they may contain spaces.

| Line | When ([20-client.md](20-client.md)) |
|---|---|
| `LOGGED_IN name=<name>` | `login_ok` received |
| `QUEUED id=<id> to=<to>` | `/send` added a message to the outbox |
| `SENT id=<id> seq=<seq> to=<to>` | `ack` received for the in-flight message |
| `RECV seq=<seq> id=<id> from=<from> text=<text>` | a `deliver` not seen before |
| `ERROR code=<code> message=<message>` | an error without a message reference |
| `ERROR code=<code> ref=<id> message=<message>` | an error about one message |
| `OFFLINE` | `/offline` closed the connection |
| `DISCONNECTED` | the connection closed while `connecting` or `online`, and the client did not close it |
| `BYE` | `/quit` or end of input |

`<seq>` is written in decimal with no leading zeros. `<id>` is the lowercase UUID.

### Escaping

In `<text>` and `<message>`, these characters are replaced, and nothing else changes:

| Character | Written as |
|---|---|
| `\` (backslash) | `\\` |
| line feed (U+000A) | `\n` |
| carriage return (U+000D) | `\r` |
| tab (U+0009) | `\t` |

Input is never unescaped: typing `a\nb` sends the four characters `a`, `\`, `n`, `b`, which a
receiver prints as `text=a\\nb`. Typing a real tab sends a tab, printed as `\t`.

### Error lines

Errors from the server are printed with the server's `code`, `ref` (if present) and `message`.
Errors the client raises itself use these exact values:

| `code` | `ref` | `message` | Cause |
|---|---|---|---|
| `unknown_command` | — | `unknown command` | line is not a known command |
| `usage` | — | `usage: /login <name>` | bad `/login` syntax |
| `usage` | — | `usage: /send <user> <text>` | bad `/send` syntax |
| `usage` | — | `usage: /online` | bad `/online` syntax |
| `usage` | — | `usage: /offline` | bad `/offline` syntax |
| `usage` | — | `usage: /quit` | bad `/quit` syntax |
| `already_logged_in` | — | `already logged in` | `/login` when not `idle` |
| `not_logged_in` | — | `log in first with /login <name>` | `/send`, `/online` or `/offline` when `idle` |
| `already_online` | — | `already online or connecting` | `/online` when `connecting` or `online` |
| `already_offline` | — | `already offline` | `/offline` when `offline` |
| `connect_failed` | — | `cannot connect to <url>` | connection could not be opened; `<url>` is the server URL as given |

## Example session

Input lines are shown after `>`; they are not part of the output.
```
> /send bob hello
ERROR code=not_logged_in message=log in first with /login <name>
> /login alice
LOGGED_IN name=alice
> /send bob Hi Bob, I have something important to tell you
QUEUED id=0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11 to=bob
SENT id=0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11 seq=1 to=bob
RECV seq=2 id=5d2e8a90-7c1b-4f3e-8d6a-2b9c4e1f0a77 from=bob text=What is it?
> /offline
OFFLINE
> /send bob I am on a plane
QUEUED id=9e1d7c2a-4b3f-4a8e-b1c6-7d5e3f2a1b09 to=bob
> /quit
BYE
```
Started again later (same data directory), the client goes online by itself:
```
LOGGED_IN name=alice
SENT id=9e1d7c2a-4b3f-4a8e-b1c6-7d5e3f2a1b09 seq=3 to=bob
```
