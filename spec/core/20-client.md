# 20 — Client behavior

How a client reacts to user commands and to frames. The exact command syntax and output lines
are in [30-cli.md](30-cli.md); this file refers to output lines by their first word
(`LOGGED_IN`, `SENT`, `RECV`, `ERROR`, `DISCONNECTED`, `BYE`).

## State

A client has exactly one connection state:

| State | Meaning |
|---|---|
| `idle` | No connection. The state at startup. |
| `connecting` | A connection is being opened, or `login` was sent and no answer has arrived. |
| `online` | `login_ok` was received. `name` is the logged-in name. |

It also keeps, for the life of the process:
- the **send queue**: a FIFO list of messages (`id`, `to`, `text`) not yet acknowledged. The
  first entry is **in flight** once its `send` frame has been written.
- the **seen set**: the (`from`, `id`) pairs of received messages already shown.

Nothing is written to disk in spec version 1.

## Login

`/login <name>`:
1. If the state is not `idle`: print `ERROR` `already_logged_in`. Nothing else happens.
2. Otherwise set the state to `connecting` and open a connection to the server URL.
3. If the connection cannot be opened: print `ERROR` `connect_failed`, state back to `idle`.
4. Once open, send `{"type":"login","name":<name>}` with the name exactly as typed.
5. On `login_ok`: state becomes `online`, print `LOGGED_IN` with the `name` from the frame.
   Then start sending the send queue (it is always empty here in v1).
6. On an `error` frame before `login_ok`: print it as `ERROR`, close the connection, and
   go back to `idle` without printing `DISCONNECTED`. The user can try `/login` again.
7. If the connection closes before `login_ok`: print `DISCONNECTED`, state back to `idle`.

## Sending

`/send <to> <text>`:
1. If the state is not `online`: print `ERROR` `not_logged_in`. The message is not queued.
2. Otherwise create a message with a new `id`, `to` and `text` exactly as typed, and append it
   to the send queue. Nothing is printed yet.
3. If no message is in flight, send the first queued one.

Sending the queue, one message at a time:
- Write `{"type":"send","id":…,"to":…,"text":…}` for the first queued message. It is now in flight.
- Wait. Do not write another `send` frame until one of these happens:
  - **`ack` with the in-flight `id`**: remove it from the queue and print `SENT`.
    Then send the next queued message, if any.
  - **`error` with `ref` equal to the in-flight `id`**: remove it from the queue and print
    the `ERROR` (with `ref`). Then send the next queued message, if any.
  - **The connection closes**: see [Disconnection](#disconnection).
- There is no timeout. The server answers every `send` (see protocol rule 6).

An `ack` whose `id` is not the in-flight one is ignored.

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

## Disconnection

When the connection closes while `online`, for any reason (server stopped, `session_replaced`,
network error):
1. For every message still in the send queue, oldest first, print `ERROR` `not_sent` with
   `ref` set to its `id`, and remove it. (Spec version 1 has no outbox; the loss is reported.)
2. Print `DISCONNECTED`.
3. State becomes `idle`. The client does not reconnect by itself. The user can `/login` again.

An `error` frame that arrives just before the close (such as `session_replaced`) is printed
first, as usual.

`DISCONNECTED` is printed only when the client did not close the connection itself. Closing
it on purpose (login step 6, `/quit`) prints nothing extra.

## Quitting

`/quit`, or end of input on stdin:
1. Print `BYE`.
2. Close the connection if there is one. Messages still in the send queue are dropped
   without output.
3. Exit with status 0. Nothing is printed after `BYE`.

## Concurrency

User commands and incoming frames are handled one at a time, each to completion, in the
order they become available. Output lines appear in the order the events were handled.
A client MUST NOT wait for user input before handling frames, or the reverse.
