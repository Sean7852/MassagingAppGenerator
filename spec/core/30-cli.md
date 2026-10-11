# 30 — CLI contract

Everything observable about a client from outside the process. Conformance tests compare this
output byte for byte, so every client MUST produce exactly these lines.

## Invocation

```
<platform run command> [--server <url>]
```
- `--server <url>`: WebSocket URL of the server. Default `ws://127.0.0.1:8765`.
- Any other argument: print a usage message to **stderr** and exit with status 2.
- The client does not connect at startup. It prints nothing until the first command.

## Input (stdin)

- UTF-8 text, one command per line. A line ends at `\n`; a `\r` right before it is removed.
  Nothing else is trimmed.
- An empty line is ignored (no output).
- A line is parsed by these rules, first match wins:

| Line | Command |
|---|---|
| matches `^/login ([^ ]+)$` | login with that name |
| matches `^/send ([^ ]+) (.+)$` | send group 2 (the text, kept exactly, spaces included) to group 1 |
| is exactly `/quit` | quit |
| starts with `/login`, `/send` or `/quit` followed by a space or end of line | usage error |
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
| `SENT id=<id> seq=<seq> to=<to>` | `ack` received for the in-flight message |
| `RECV seq=<seq> id=<id> from=<from> text=<text>` | a `deliver` not seen before |
| `ERROR code=<code> message=<message>` | an error without a message reference |
| `ERROR code=<code> ref=<id> message=<message>` | an error about one message |
| `DISCONNECTED` | the connection closed while `connecting` or `online` |
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
| `usage` | — | `usage: /quit` | bad `/quit` syntax |
| `already_logged_in` | — | `already logged in or connecting` | `/login` when not `idle` |
| `not_logged_in` | — | `log in first with /login <name>` | `/send` when not `online` |
| `connect_failed` | — | `cannot connect to <url>` | connection could not be opened; `<url>` is the server URL as given |
| `not_sent` | message `id` | `connection lost before the server acknowledged the message` | connection closed with the message still queued |

## Example session

Input lines are shown after `>`; they are not part of the output.
```
> /send bob hello
ERROR code=not_logged_in message=log in first with /login <name>
> /login alice
LOGGED_IN name=alice
> /send bob Hi Bob, I have something important to tell you
SENT id=0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11 seq=1 to=bob
RECV seq=2 id=5d2e8a90-7c1b-4f3e-8d6a-2b9c4e1f0a77 from=bob text=What is it?
> /send Bob hi
ERROR code=invalid_name ref=c3a1e2b4-9f8d-4c7b-a6e5-1d2c3b4a5f60 message=to must match ^[a-z0-9_]{1,32}$
> /quit
BYE
```
