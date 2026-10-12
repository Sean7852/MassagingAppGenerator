# 40 — Storage

What a client keeps on disk, so that the user's name and unsent messages survive a restart or
a crash. Every client stores exactly the same data in exactly the same format, so the file can
be inspected, and a data directory written by one client can be used by another.

## Data directory

- Chosen with `--data-dir <dir>` ([30-cli.md](30-cli.md#invocation)); default `.msgdata`,
  relative to the current working directory.
- One data directory belongs to one user. Two clients running at the same time must use
  different data directories.
- The client creates the directory (and any missing parents) the first time it saves.
  Starting and running without ever saving creates nothing.

## The state file

`<data-dir>/state.json`, a UTF-8 JSON object:

```json
{
  "version": 1,
  "name": "alice",
  "outbox": [
    {"id": "0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11", "to": "bob", "text": "Hi Bob"}
  ]
}
```

| Field | Type | Meaning |
|---|---|---|
| `version` | integer, always `1` | Format version of this file. |
| `name` | string, or `null` | The saved name, or `null` before the first successful login. |
| `outbox` | array of objects | The outbox, oldest message first. Each has `id`, `to`, `text` (strings). |

Whitespace, indentation and field order in the file do not matter.

## Saving

- "Save" means: write the complete state to `<data-dir>/state.json.tmp`, then rename it over
  `<data-dir>/state.json` (replacing it). A crash at any moment leaves either the old or the
  new file, never a partial one.
- The client saves after every change to the name or the outbox, and **before** printing the
  line that reports the change (`LOGGED_IN` after `/login`, `QUEUED`, `SENT`, and `ERROR` with
  a `ref`). So a line on stdout always means the change is already on disk.
- If saving fails (for example the directory cannot be written): print a message on stderr
  and exit with status 1, without printing the line for that change.

## Loading

At startup:
- If `<data-dir>/state.json` does not exist: no name, empty outbox.
- If it exists and is valid (the format above, `version` 1): use it. Unknown extra fields are
  ignored.
- If it exists but cannot be read or is not valid: print a message on stderr and exit with
  status 1, leaving the file untouched. The client never discards saved messages on its own.
- A leftover `state.json.tmp` is ignored (it is replaced on the next save).

The seen set is not stored. After a restart, a message the server delivers again (because its
`deliver_ack` was lost) may be shown a second time; protocol rule 5 makes this rare.
