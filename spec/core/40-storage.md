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
| `version` | the number `1` | Format version of this file. |
| `name` | string, or `null` | The saved name, or `null` before the first successful login. |
| `outbox` | array of objects | The outbox, oldest message first. Each has `id`, `to`, `text` (strings). |

Whitespace, indentation and field order in the file do not matter.

### What makes the file valid

The file is valid only if **all** of these hold:
1. It is UTF-8 JSON (no byte order mark) whose top level is an object.
2. `version` is present and is the number 1 (not `true`, not `"1"`).
3. `name` is present and is either `null` or a non-empty string.
4. `outbox` is present and is an array. If `name` is `null`, the array is empty.
5. Every outbox entry is an object with:
   - `id`: a string matching `^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`;
   - `to`: a non-empty string;
   - `text`: a non-empty string of at most 8192 bytes in UTF-8.
6. No two outbox entries have the same `id`.

Extra fields, at the top level or in an entry, are allowed and ignored; they are not written
back on the next save.

(Rule 5 matters: an `id` the server cannot read is rejected without a `ref`, so the client
would wait for an answer forever and nothing after it would ever be sent.)

## Saving

- "Save" means: write the complete state to `<data-dir>/state.json.tmp`, flush it to disk
  (fsync), then rename it over `<data-dir>/state.json` (replacing it). A crash at any moment
  leaves either the old or the new file, never a partial one.
- The client saves after every change to the name or the outbox, and **before** printing the
  line that reports the change (`LOGGED_IN` after `/login`, `QUEUED`, `SENT`, and `ERROR` with
  a `ref`). So a line on stdout always means the change is already on disk.
- If saving fails (for example the directory cannot be written): print a message on stderr
  and exit with status 1, without printing the line for that change.

## Loading

At startup:
- If `<data-dir>/state.json` does not exist: no name, empty outbox.
- If it exists and is [valid](#what-makes-the-file-valid): use it.
- If it exists but cannot be read or is not valid: print a message on stderr and exit with
  status 1, leaving the file untouched. The client never discards saved messages on its own.
- A leftover `state.json.tmp` is ignored (it is replaced on the next save).

The seen set is not stored. After a restart, a message the server delivers again (because its
`deliver_ack` was lost) may be shown a second time; protocol rule 5 makes this rare.
