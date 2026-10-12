# Extension 10 — Read receipts

When a user's client shows a message, the message's sender is told, and their client prints
that the message was read. There is no new command: receipts are automatic.

This module only **adds** to the core modules; every core rule still holds. Each section says
which core module it extends.

## How it works

A receiving client already confirms every message it shows, with `deliver_ack`
([../core/20-client.md](../core/20-client.md#receiving)). The server turns that confirmation
into a **receipt** for the sender. So the receiving client needs no change; only the
sending client handles one new frame. A client that does not know this extension ignores the
new frame ([../core/10-protocol.md](../core/10-protocol.md#transport)), so old clients keep
working.

## Protocol (extends 10-protocol.md)

### New frame: server → client

| `type` | Fields | Meaning |
|---|---|---|
| `receipt` | `seq` (integer), `msg_seq` (integer), `msg_id` (string), `by` (string) | User `by` has shown the message with `msg_seq` / `msg_id` that this user sent. `seq` is the receipt's own number. |

Example:
```json
{"type":"receipt","seq":4,"msg_seq":3,"msg_id":"0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11","by":"bob"}
```

### New server rules
1. When the server receives the **first** `deliver_ack` for a message, it creates a receipt for
   that message's sender. A later `deliver_ack` for the same message creates nothing (core
   rule 8 already ignores it). So there is at most one receipt per message.
2. No receipt is created for a message a user sent to themselves.
3. A receipt takes the next `seq` from the same counter as messages, and is stored and
   delivered exactly like a message (core rules 3–5): it goes into the sender's mailbox, is
   pushed at once if the sender is online, is sent after `login_ok` otherwise, in `seq` order
   together with messages, and stays until the sender's client sends `deliver_ack` with the
   receipt's `seq`.

## Client behavior (extends 20-client.md)

On a `receipt` frame while `online` (the rules for old connections and broken frames apply as
for any frame):
1. If (`by`, `msg_id`) is in the **seen receipts** set: print nothing.
   Otherwise add it to that set and print `READ`.
2. Then, in both cases, send `{"type":"deliver_ack","seq":<seq>}` with the receipt's `seq`.

The seen receipts set is kept in memory for the life of the process, like the seen set for
messages, and is not saved. The client does not check that `msg_id` is one of its own messages.

A receipt is required to have all four fields with the types above; otherwise it is a broken
frame and is ignored ([../core/90-defaults.md](../core/90-defaults.md) rule 2; `seq` and
`msg_seq` follow the same number rules as `seq` there).

## Output (extends 30-cli.md)

| Event | Machine line (`--machine`) | Friendly line |
|---|---|---|
| `READ` | `READ id=<msg_id> seq=<msg_seq> by=<by>` | `[read]   by <by> (#<msg_seq>)` (three spaces after `[read]`) |

`<msg_id>` and `<by>` are written unchanged; `<msg_seq>` in decimal with no leading zeros.
The receipt's own `seq` is never printed.

## Timing

A receipt for a message arrives after that message's `SENT` line, because the server answers
the sender before it delivers to the recipient. It may arrive before or after the sender's
other lines (for example the `SENT` of the next message), depending on timing.
