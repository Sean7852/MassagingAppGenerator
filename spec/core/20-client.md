# 20 — Client behavior

How a client reacts to user commands and to frames. The exact command syntax and output lines
are in [30-cli.md](30-cli.md); this file refers to output lines by their first word
(`LOGGED_IN`, `QUEUED`, `SENT`, `RECV`, `ERROR`, `OFFLINE`, `DISCONNECTED`, `BYE`).
Saved state and its file format are in [40-storage.md](40-storage.md).

## State

A client has exactly one connection state:

| State | Meaning |
|---|---|
| `idle` | No saved name. The user has never logged in with this data directory. |
| `offline` | A name is saved, and there is no connection. |
| `connecting` | A connection is being opened, or `login` was sent and no answer has arrived. |
| `online` | `login_ok` was received. |

It also keeps:
- the **saved name** and the **outbox**, which are stored on disk ([40-storage.md](40-storage.md)):
  - the **name** the user logged in with, or none;
  - the **outbox**: a FIFO list of messages (`id`, `to`, `text`) the server has not yet
    accepted or rejected. The first entry is **in flight** once its `send` frame has been
    written on the current connection.
- the **seen set**, in memory for the life of the process: the (`from`, `id`) pairs of received
  messages already shown.

## Startup

1. Load the saved state ([40-storage.md](40-storage.md#loading)).
2. If no name is saved: the state is `idle`. Print nothing; wait for commands.
3. If a name is saved: the state is `offline`, and the client immediately
   [goes online](#going-online) as if the user had typed `/online`.

## Going online

Used by `/online` and at startup, with the saved name `N`.

**Going online holds everything up.** From the moment it starts until its outcome is known
(`login_ok`, an `error`, the connection failing to open, or the connection closing), the client
handles no other command. Commands typed meanwhile wait, in order, and are handled afterwards.
So a command never sees the state `connecting`.

1. Set the state to `connecting` and open a connection to the server URL. The connection is
   **open** when the WebSocket handshake has completed.
2. If the connection cannot be opened, or is not open within **5 seconds**: print `ERROR`
   `connect_failed`. State becomes `offline`.
3. Once open, send `{"type":"login","name":N}`.
4. On `login_ok`: state becomes `online`, print `LOGGED_IN` with the `name` from the frame,
   then [start sending the outbox](#sending-the-outbox).
5. On an `error` frame before `login_ok`: print it as `ERROR`, close the connection,
   state becomes `offline`. No `DISCONNECTED` is printed.
6. If the connection closes before `login_ok`: print `DISCONNECTED`. State becomes `offline`.

## Commands

### `/login <name>`
1. If the state is not `idle`: print `ERROR` `already_logged_in`. Nothing else happens.
   (A data directory belongs to one user. Use another data directory for another user.)
2. Otherwise go online as above, with the name exactly as typed, except:
   - on `login_ok`, first save the `name` from the frame, then print `LOGGED_IN`;
   - wherever the steps above say the state becomes `offline`, it becomes `idle` instead,
     and nothing is saved.

### `/online`
- `idle`: print `ERROR` `not_logged_in`.
- `offline`: [go online](#going-online).
- `online`: print `ERROR` `already_online`.

### `/offline`
- `idle`: print `ERROR` `not_logged_in`.
- `offline`: print `ERROR` `already_offline`.
- `online`: close the connection, set the state to `offline`, and print `OFFLINE`. A message that was in flight stays first in the outbox and is no longer in flight.
  `DISCONNECTED` is not printed, because the client closed the connection itself.

### `/send <to> <text>`
1. If the state is `idle`: print `ERROR` `not_logged_in`. Nothing is queued.
2. If the text is longer than **8192 bytes** in UTF-8: print `ERROR` `too_long`. Nothing is
   queued. (Longer texts would make a frame the server refuses, which would block the outbox.)
3. Otherwise create a message with a new `id`, and `to` and `text` exactly as typed. Append it
   to the outbox, save, then print `QUEUED`. This is the same in `offline` and `online`.
4. If the state is `online` and no message is in flight, send the first outbox message.

### `/quit`, or end of input on stdin
1. Print `BYE`.
2. Close the connection if there is one. The outbox is already saved and is sent the next
   time the client goes online.
3. Exit with status 0. Nothing is printed after `BYE`.

## Sending the outbox

One message at a time, oldest first, and only while `online`:
- Write `{"type":"send","id":…,"to":…,"text":…}` for the first outbox message. It is now in flight.
- Wait. Do not write another `send` frame until one of these happens:
  - **`ack` with the in-flight `id`**: remove the message from the outbox, save, then print
    `SENT`. Then send the next outbox message, if any.
  - **`error` with `ref` equal to the in-flight `id`**: remove the message from the outbox,
    save, then print the `ERROR` (with `ref`). Then send the next outbox message, if any.
  - **The connection closes**, or the user types `/offline`: the message stays first in the
    outbox. It is sent again, with the same `id`, the next time the client is online.
- There is no timeout. The server answers every `send` (protocol rule 6).

An `ack` whose `id` is not the in-flight one is ignored.

Sending a message again after a reconnect is safe: if the server had already accepted it, it
answers with the same `ack` (protocol rule 1), so the receiver still gets it once and the
sender prints `SENT` once.

After `login_ok` the server first sends the messages waiting for this user, before it has seen
any `send` on the new connection. So after a reconnect, the `RECV` lines for waiting messages
come before the `SENT` line of the first outbox message.

## Receiving

On a `deliver` frame while `online`:
1. If (`from`, `id`) is in the seen set: print nothing.
   Otherwise add it to the seen set and print `RECV`.
2. Then, in both cases, send `{"type":"deliver_ack","seq":<seq>}`.

Frames are handled one at a time in the order they arrive. `deliver` frames are not reordered
by `seq`; the server already sends them in order.

## Other frames

- An `error` frame while `online` whose `ref` is not the in-flight `id` (or that has no `ref`):
  print it as `ERROR` and change nothing else.
- `login_ok` while `online`, and any frame of an unknown `type`: ignore.
- While `connecting`, only `login_ok` and `error` count; any other frame is ignored.
- A frame that breaks the rules for its type is ignored ([90-defaults.md](90-defaults.md) rule 2).

## Old connections

Every frame and every "connection closed" event belongs to one connection. Once the client has
closed a connection, or a new one has replaced it, anything still arriving from the old one is
ignored: no output, no `deliver_ack`, no state change. In `idle` and `offline` there is no
current connection, so every frame is ignored.

Nothing is lost this way: a `deliver` that was ignored is not acknowledged, so the server
delivers it again on the next login (protocol rule 5).

## Keep-alive

While a connection is open, the client sends a WebSocket **ping** every **20 seconds**. If no
**pong** arrives within **20 seconds** of a ping, the connection counts as lost: the client
closes it and handles it as a [disconnection](#disconnection) (`DISCONNECTED`). This is how a
client notices a network that died without closing the connection. Pings and pongs are
WebSocket control frames, not JSON frames, and never produce output.

## Disconnection

When the connection closes and the client did not close it itself (server stopped,
`session_replaced`, network error, keep-alive timeout), while `online`:
1. A message that was in flight stays first in the outbox and is no longer in flight.
2. Print `DISCONNECTED`.
3. State becomes `offline`. The client does not reconnect by itself; the user types `/online`.

While `connecting`, see [Going online](#going-online) step 6 (and `/login` for `idle`).

An `error` frame that arrives just before the close (such as `session_replaced`) is printed
first, as usual. `DISCONNECTED` is printed only when the client did not close the connection
itself; closing it on purpose (`/offline`, a rejected login, `/quit`) prints nothing extra.

## Concurrency

User commands and incoming frames are handled one at a time, each to completion, in the
order they become available. Output lines appear in the order the events were handled.
A client MUST NOT wait for user input before handling frames, or the reverse.

The one exception is [going online](#going-online): it is handled to completion, including
waiting for the connection and the login answer, before the next command is handled.
