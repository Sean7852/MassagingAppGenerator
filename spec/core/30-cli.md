# 30 — CLI contract

Everything observable about a client from outside the process. Tests compare the output byte for
byte, so every client MUST produce exactly these lines, in both output modes.

## Invocation

```
<platform run command> [--server <url>] [--data-dir <dir>] [--machine]
```
- `--server <url>`: WebSocket URL of the server. Default `ws://127.0.0.1:8765`.
- `--data-dir <dir>`: where each user's outbox is saved, in one folder per user
  ([40-storage.md](40-storage.md)). Default `.msgdata`, relative to the current working
  directory. Normal use never needs it.
- `--machine`: print [machine lines](#machine-lines) instead of [friendly lines](#friendly-lines).
  Tests use this mode.

The arguments are exactly these. `--server` and `--data-dir` take a value either as the next
argument or after `=` (`--server=ws://…`); the value must not be empty. Each option may appear
at most once, in any order. **Anything else** (an unknown option, `-h` or `--help`, a
shortened option such as `--serv`, a repeated option, a missing or empty value, a positional
argument) is an error: print a usage message to **stderr** and exit with status 2.

Arguments are checked before anything else. Every launch starts logged out: the client
prints nothing until the first command, and the user types `/login <name>`
([20-client.md](20-client.md#startup)).

Exit status: 0 after `BYE`; 2 for bad arguments; 1 when a user's saved outbox cannot be
loaded (at `/login`) or saved ([40-storage.md](40-storage.md)), with a message on stderr.

Signals (Ctrl+C, SIGTERM) and a closed stdout are **out of scope**: what the client prints or
returns then is not specified and not tested.

## Input (stdin)

- UTF-8 text, one command per line. A line ends at `\r\n`, `\n`, or a lone `\r`; the line
  ending is removed and nothing else is trimmed. So `\r` can never be part of a command.
  A last line with no line ending before end of input is still a line.
- Bytes that are not valid UTF-8 are read as U+FFFD (`�`), one per invalid sequence, and the
  line is handled normally.
- An empty line is ignored (no output).
- End of input (stdin closed) behaves like `/quit`.

### Commands

"Space" below means the space character U+0020 only. Each line is checked against these rows,
first match wins:

| The line | Command |
|---|---|
| is exactly `/online` | go online |
| is exactly `/offline` | go offline |
| is exactly `/quit` | quit |
| is `/login`, a space, then a **name**: one or more characters, none of them a space | log in with that name |
| is `/send`, a space, then a **name**: one or more characters up to the next space, then that space, then the **text**: **everything after it to the end of the line**, at least one character, whatever characters it contains (spaces included) | send the text to the name |
| is `/login`, `/send`, `/online`, `/offline` or `/quit`, alone or followed by a space, and matched no row above | usage error for that command |
| anything else | unknown command |

Examples:

| Line | Result |
|---|---|
| `/send bob hi there` | send `hi there` to `bob` |
| `/send bob  hi` | send ` hi` (with a leading space) to `bob` |
| `/send bob` or `/send bob ` | usage error (no text) |
| `/send  bob hi` | usage error (empty name) |
| `/sendx bob hi` | unknown command |
| `/login alice bob` | usage error (a name has no spaces) |

The text is taken as it is, whatever it contains: any letter, emoji, tab, or rare invisible
character such as U+2028 (line separator) is part of the text. Names are not checked by the
client ([10-protocol.md](10-protocol.md#names)).

## Output (stdout)

- UTF-8, one event per line, each line ending with `\n` only (never `\r\n`), written and
  flushed as soon as the event happens.
- Only the lines below are ever written to stdout. No prompts, banners, colors or logging.
  Diagnostics MAY go to stderr, which is never compared.
- `<text>` and `<message>` are **escaped** (see below). All other values (`<name>`, `<to>`,
  `<from>`, `<id>`, `<seq>`, `<url>`) are written unchanged.
- `<seq>` is written in decimal with no leading zeros. `<id>` is the lowercase UUID.

Each event has one machine line and one friendly line. [20-client.md](20-client.md) names
events by their machine keyword.

### Machine lines

Printed with `--machine`. Fields are separated by one space, in exactly this order; `<text>`
and `<message>` come last because they may contain spaces.

| Line | When ([20-client.md](20-client.md)) |
|---|---|
| `LOGGED_IN name=<name>` | `login_ok` received |
| `QUEUED id=<id> to=<to>` | `/send` added a message to the outbox |
| `SENT id=<id> seq=<seq> to=<to>` | `ack` received for the in-flight message |
| `RECV seq=<seq> id=<id> from=<from> text=<text>` | a `deliver` not seen before |
| `ERROR code=<code> message=<message>` | an error without a message reference |
| `ERROR code=<code> ref=<id> message=<message>` | an error about one message |
| `OFFLINE` | `/offline` closed the connection, or `/login` could not connect (the user is logged in, offline) |
| `DISCONNECTED` | the connection closed while `connecting` or `online`, and the client did not close it |
| `BYE` | `/quit` or end of input |

### Friendly lines

Printed by default (without `--machine`). Exactly these texts, with the values filled in:

| Event | Friendly line |
|---|---|
| `LOGGED_IN` | `Logged in as <name>` |
| `QUEUED` | `[queued] to <to>: <text>` |
| `SENT` | `[sent]   to <to> (#<seq>)` (three spaces after `[sent]`) |
| `RECV` | `[<from>] <text>` |
| `ERROR` (with or without `ref`) | `Error: <message>` |
| `OFFLINE` | `You are offline. Messages will be queued.` |
| `DISCONNECTED` | `Disconnected. Type /online to reconnect.` |
| `BYE` | `Bye.` |

`<text>` in `QUEUED` is the text of the message that was queued.

### Escaping

In `<text>` and `<message>`, in both modes, these characters are replaced, and nothing else
changes:

| Character | Written as |
|---|---|
| `\` (backslash) | `\\` |
| line feed (U+000A) | `\n` |
| carriage return (U+000D) | `\r` |
| tab (U+0009) | `\t` |
| a lone surrogate (U+D800 to U+DFFF not part of a valid pair; it can arrive in JSON from a sender that is not one of our clients) | U+FFFD (`�`) |

Input is never unescaped: typing `a\nb` sends the four characters `a`, `\`, `n`, `b`, which a
receiver prints as `a\\nb`. Typing a real tab sends a tab, printed as `\t`.

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
| `invalid_name` | — | `name must match ^[a-z0-9_]{1,32}$` | `/login` with a name that breaks the name rule (the same line the server would give) |
| `not_logged_in` | — | `log in first with /login <name>` | `/send`, `/online` or `/offline` when `idle` |
| `already_online` | — | `already online` | `/online` when `online` |
| `already_offline` | — | `already offline` | `/offline` when `offline` |
| `too_long` | — | `message too long (max 8192 bytes)` | `/send` text over 8192 bytes in UTF-8 |
| `connect_failed` | — | `cannot connect to <url>` | connection could not be opened within 5 s; `<url>` is the server URL as given |

## Example session

Input lines are shown after `>`; they are not part of the output.

Friendly (default):
```
> /send bob hello
Error: log in first with /login <name>
> /login alice
Logged in as alice
> /send bob Hi Bob, I have something important to tell you
[queued] to bob: Hi Bob, I have something important to tell you
[sent]   to bob (#1)
[bob] What is it?
> /offline
You are offline. Messages will be queued.
> /send bob I am on a plane
[queued] to bob: I am on a plane
> /quit
Bye.
```

The same session with `--machine`:
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
Started again later, Alice logs in and her queued message goes out:
```
> /login alice
Logged in as alice
[sent]   to bob (#3)
```
If the server is down at `/login`, she is logged in offline and can still queue messages:
```
> /login alice
Error: cannot connect to ws://127.0.0.1:8765
You are offline. Messages will be queued.
```
