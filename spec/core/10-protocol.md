# 10 — Protocol

The wire protocol between a client and the server. `server/server.py` implements the server side.

## Transport
- One WebSocket connection per client session. The client chooses the URL; the default is
  `ws://127.0.0.1:8765`.
- Every frame is one WebSocket **text** message containing one JSON object, UTF-8 encoded, at
  most 64 KiB. The object always has a string field `type`.
- A receiver MUST ignore fields it does not know. A client MUST ignore frames whose `type` it
  does not know. (This keeps old clients working when extensions add fields or frames.)
- A client ignores binary WebSocket messages.
- WebSocket ping and pong control frames are used for keep-alive
  ([20-client.md](20-client.md#keep-alive)); each side answers a ping with a pong.
- Clients connect directly: no HTTP proxy, even if the environment configures one. HTTP
  redirects are out of scope (the server never sends one).
- Field names and `type` values are exact and case-sensitive.

## Names
A user name matches `^[a-z0-9_]{1,32}$`. Only the server checks this; clients send what the user
typed and report the server's answer.

## Frames: client → server

| `type` | Fields | When |
|---|---|---|
| `login` | `name` (string) | First frame on every connection. |
| `send` | `id` (string), `to` (string), `text` (string) | Send a message. |
| `deliver_ack` | `seq` (integer) | After the client has shown the message with this `seq`. |

Examples:
```json
{"type":"login","name":"alice"}
{"type":"send","id":"0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11","to":"bob","text":"Hi Bob"}
{"type":"deliver_ack","seq":1}
```

## Frames: server → client

| `type` | Fields | Meaning |
|---|---|---|
| `login_ok` | `name` | Login accepted. Waiting messages follow as `deliver` frames. |
| `ack` | `id`, `seq` | The message with this `id` from this user is accepted and stored. |
| `deliver` | `seq`, `id`, `from`, `to`, `text` | A message for this user. |
| `error` | `code`, `message`, optional `ref` | Something was rejected. `ref` is the `id` of the rejected `send`, when the error is about one. |

Examples:
```json
{"type":"login_ok","name":"alice"}
{"type":"ack","id":"0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11","seq":1}
{"type":"deliver","seq":1,"id":"0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11","from":"alice","to":"bob","text":"Hi Bob"}
{"type":"error","code":"invalid_name","message":"to must match ^[a-z0-9_]{1,32}$","ref":"0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11"}
```

### Error codes
| `code` | Cause | Connection |
|---|---|---|
| `not_logged_in` | A frame other than `login` came first. | stays open |
| `already_logged_in` | `login` on a connection that is already logged in. | stays open |
| `invalid_name` | `name` or `to` does not match the name rule. | stays open |
| `bad_request` | Not JSON, not an object, missing or wrong-typed field, `id` not a lowercase UUID, `text` empty or longer than 4096 characters. | stays open |
| `unknown_type` | Unknown `type`. | stays open |
| `session_replaced` | The same name logged in on another connection. | closed by server with close code `4001` |

`message` is human-readable text. Clients show it but never act on it.

## Server rules
1. **Dedup.** The server keys messages by (sender, `id`). Sending a pair it already accepted
   returns the same `ack` (same `seq`) and does not store or deliver the message again.
2. **Sequencing.** On first acceptance the server assigns the next `seq` (1, 2, 3, … across the
   whole server).
3. **Store and forward.** An accepted message goes into the recipient's mailbox whether or not
   the recipient is online or has ever logged in. It stays there until the recipient sends
   `deliver_ack` with its `seq`.
4. **Delivery.** After `login_ok` the server sends every mailbox message in `seq` order. New
   messages are pushed to an online recipient right away. Frames on one connection always
   arrive in the order the server produced them.
5. **Redelivery.** A message that was delivered but not acknowledged with `deliver_ack` is
   delivered again on the recipient's next login.
6. **Ack order.** The server answers each `send` with exactly one `ack` or one `error` with
   `ref`, in the order the `send` frames arrived. For a message to yourself, the `ack` comes
   before the `deliver`.
7. **Second login.** When a name logs in while already logged in elsewhere, the newest
   connection wins: the old one receives `error` `session_replaced` and is closed.
8. **`deliver_ack`** for an unknown or already acknowledged `seq` is ignored, with no reply.
9. Sending to yourself is allowed.
