# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""Saved state: name and outbox in <data-dir>/state.json (40-storage.md)."""
import json
import os
import pathlib
import re

MAX_TEXT_BYTES = 8192
_ID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


class StateError(Exception):
    pass


def _is_one(v):
    if type(v) is int:
        return v == 1
    if type(v) is float:
        return v == 1.0
    return False


def _non_empty_str(v):
    return isinstance(v, str) and v != ""


def utf8_len(s):
    return len(s.encode("utf-8"))


def parse_state(data):
    """Validate the bytes of a state file. Return (name, outbox) or raise StateError."""
    if data.startswith(b"\xef\xbb\xbf"):
        raise StateError("state file starts with a byte order mark")
    try:
        text = data.decode("utf-8")
        obj = json.loads(text)
    except (UnicodeDecodeError, ValueError) as e:
        raise StateError(f"state file is not UTF-8 JSON: {e}")
    if not isinstance(obj, dict):
        raise StateError("state file top level is not an object")
    if "version" not in obj or not _is_one(obj["version"]):
        raise StateError("version must be the number 1")
    if "name" not in obj:
        raise StateError("name is missing")
    name = obj["name"]
    if name is not None and not _non_empty_str(name):
        raise StateError("name must be null or a non-empty string")
    if "outbox" not in obj or not isinstance(obj["outbox"], list):
        raise StateError("outbox must be an array")
    entries = obj["outbox"]
    if name is None and entries:
        raise StateError("outbox must be empty when name is null")
    outbox = []
    ids = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise StateError("outbox entry is not an object")
        id_ = entry.get("id")
        to = entry.get("to")
        text_ = entry.get("text")
        if not isinstance(id_, str) or not _ID_RE.fullmatch(id_):
            raise StateError("outbox entry has a bad id")
        if not _non_empty_str(to):
            raise StateError("outbox entry has a bad to")
        if not _non_empty_str(text_):
            raise StateError("outbox entry has a bad text")
        try:
            too_long = utf8_len(text_) > MAX_TEXT_BYTES
        except UnicodeEncodeError:
            raise StateError("outbox entry text is not valid Unicode")
        if too_long:
            raise StateError("outbox entry text is longer than 8192 bytes")
        if id_ in ids:
            raise StateError("two outbox entries have the same id")
        ids.add(id_)
        outbox.append({"id": id_, "to": to, "text": text_})
    return name, outbox


def load_state(data_dir):
    """Return (name, outbox). Raise StateError if the file exists but is unusable."""
    path = pathlib.Path(data_dir) / "state.json"
    if not path.exists():
        return None, []
    try:
        data = path.read_bytes()
    except OSError as e:
        raise StateError(f"cannot read {path}: {e}")
    return parse_state(data)


def save_state(data_dir, name, outbox):
    """Atomically write the state file. Raises OSError on failure."""
    directory = pathlib.Path(data_dir)
    directory.mkdir(parents=True, exist_ok=True)
    tmp = directory / "state.json.tmp"
    state = {
        "version": 1,
        "name": name,
        "outbox": [{"id": m["id"], "to": m["to"], "text": m["text"]} for m in outbox],
    }
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(state, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, directory / "state.json")
