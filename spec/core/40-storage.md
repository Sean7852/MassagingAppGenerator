# 40 — Storage

What a client keeps on disk, so that a user's unsent messages survive a restart or a crash.
Every client stores exactly the same data in exactly the same format, so the file can be
inspected, and a folder written by one client can be used by another.

The user's name is **not** stored: every launch starts logged out, and the user types `/login`
([20-client.md](20-client.md#login-name)). The name only chooses which folder to use.

## Folders

- The **data directory** is chosen with `--data-dir <dir>` ([30-cli.md](30-cli.md#invocation));
  default `.msgdata`, relative to the current working directory. Normal use never needs the
  option.
- Each user has their own folder inside it, named exactly after the user:
  `<data-dir>/<name>/`. So `/login alice` uses `.msgdata/alice/`, and two users on one machine
  never share a folder.
- The client creates the folders (and any missing parents) the first time it saves. Logging in
  and running without ever saving creates nothing.
- Two processes logged in as the same user at the same time share one folder; that is not
  supported (the last save wins).

## The state file

`<data-dir>/<name>/state.json`, a UTF-8 JSON object:

```json
{
  "version": 2,
  "outbox": [
    {"id": "0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11", "to": "bob", "text": "Hi Bob"}
  ]
}
```

| Field | Type | Meaning |
|---|---|---|
| `version` | the number `2` | Format version of this file. (Version 1, which also held the name, is no longer used.) |
| `outbox` | array of objects | The outbox, oldest message first. Each has `id`, `to`, `text` (strings). |

Whitespace, indentation and field order in the file do not matter.

### What makes the file valid

The file is valid only if **all** of these hold:
1. It is UTF-8 JSON (no byte order mark) whose top level is an object.
2. `version` is present and is the number 2 (not `true`, not `"2"`).
3. `outbox` is present and is an array.
4. Every outbox entry is an object with:
   - `id`: a string matching `^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`;
   - `to`: a non-empty string;
   - `text`: a non-empty string of at most 8192 bytes in UTF-8.
5. No two outbox entries have the same `id`.

Extra fields, at the top level or in an entry, are allowed and ignored; they are not written
back on the next save.

(Rule 4 matters: an `id` the server cannot read is rejected without a `ref`, so the client
would wait for an answer forever and nothing after it would ever be sent.)

## Saving

- "Save" means: write the complete state to `<data-dir>/<name>/state.json.tmp`, flush it to
  disk (fsync), then rename it over `<data-dir>/<name>/state.json` (replacing it). A crash at
  any moment leaves either the old or the new file, never a partial one.
- The client saves after every change to the outbox, and **before** printing the line that
  reports the change (`QUEUED`, `SENT`, and `ERROR` with a `ref`). So a line on stdout always
  means the change is already on disk.
- If saving fails (for example the directory cannot be written): print a message on stderr
  and exit with status 1, without printing the line for that change.

## Loading

When a user logs in (`/login <name>`):
- If `<data-dir>/<name>/state.json` does not exist: the outbox is empty.
- If it exists and is [valid](#what-makes-the-file-valid): use its outbox.
- If it exists but cannot be read or is not valid: print a message on stderr and exit with
  status 1, leaving the file untouched. The client never discards saved messages on its own.
- A leftover `state.json.tmp` is ignored (it is replaced on the next save).

The seen set is not stored. After a restart, a message the server delivers again (because its
`deliver_ack` was lost) may be shown a second time; protocol rule 5 makes this rare.
