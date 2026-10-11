# Wire protocol (draft, implemented by `server/server.py`)

> **Status: draft.** This describes what the server does today so the spec can be written against
> something real. It moves into `spec/core/10-protocol.md`, which then becomes authoritative,
> and this file is reduced to a pointer.

## Transport
- One WebSocket connection per client, default `ws://127.0.0.1:8765`.
- Every frame is a UTF-8 text frame holding one JSON object with a string `type`. Max 64 KiB.
- Unknown fields are ignored (forward compatibility for extensions).

## Frames

### Client → server
| type | fields | meaning |
|---|---|---|
| `login` | `name` | Must be the first frame. `name` matches `^[a-z0-9_]{1,32}$`. |
| `send` | `id`, `to`, `text` | `id` is a client-generated lowercase UUID. `text` is 1..4096 chars. |
| `deliver_ack` | `seq` | The client has stored/displayed message `seq`; the server may forget it. |

### Server → client
| type | fields | meaning |
|---|---|---|
| `login_ok` | `name` | Login accepted. Pending `deliver` frames follow immediately. |
| `ack` | `id`, `seq` | Message `id` is accepted and stored. The client removes it from its outbox. |
| `deliver` | `seq`, `id`, `from`, `to`, `text` | A message for this user. |
| `error` | `code`, `message`, optional `ref` | `ref` is the message `id` when the error is about a `send`. |

Error codes: `not_logged_in`, `already_logged_in`, `invalid_name`, `bad_request`,
`unknown_type`, `session_replaced`.

## Rules
1. **Identity and dedup.** The server keys messages by `(sender, id)`. Resending an accepted
   message returns the same `ack{id, seq}` and is not stored or delivered again.
2. **Sequencing.** `seq` is a positive integer assigned by the server on first acceptance,
   strictly increasing across the whole server.
3. **Store-and-forward.** An accepted message goes into the recipient's mailbox, whether or not
   the recipient has ever logged in. It stays there until the recipient sends `deliver_ack{seq}`.
4. **Delivery.** On login the server sends `login_ok`, then every mailbox message in `seq` order.
   New messages are pushed to an online recipient immediately. Frames on one connection are
   always sent in the order the server produced them.
5. **Redelivery.** A message that was pushed but not `deliver_ack`ed is pushed again on the next
   login. Clients must dedup by `id`.
6. **One message in flight.** A client sends its outbox oldest first and has at most one
   unanswered `send` at a time. After `login_ok` it sends the oldest outbox message, then waits
   until one of these happens:
   - `ack` for that `id` arrives: remove it from the outbox and report it sent;
   - `error` with `ref` equal to that `id` arrives: remove it from the outbox and report the error;
   - the connection closes: stop, and resend it first on the next login.

   Then it sends the next one. A new message always goes to the back of the outbox, also while
   online, and is sent through the same loop. No timeout is needed: the server answers every
   `send`. (The server itself would also accept pipelined sends, acking them in order, but
   clients must not rely on that.)
7. **Second login with the same name.** The newest connection wins. The old one receives
   `error{code: session_replaced}` and is closed with WebSocket close code `4001`.
8. **Errors** never close the connection, except `session_replaced`.
9. Sending to yourself is allowed.

## Decisions (confirmed by the human author, 2026-10-11)
- Names match `^[a-z0-9_]{1,32}$` (rule in the `login` frame).
- A second login with the same name: the newest connection wins (rule 7).
- Messages to a user who has never logged in are accepted and held until they log in (rule 3).
- Clients send their outbox one message at a time (rule 6).

## Open (to settle in spec/core)
- Whether a protocol version field is needed in `login` before extensions are added.
- Conformance tests should check `RECV` order and `SENT` order separately, not one combined
  transcript: on reconnect, pushed messages and the outbox flush interleave depending on timing.
