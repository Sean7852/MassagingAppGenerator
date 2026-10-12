# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""The state file: loading, validation and atomic saving (spec/core/40-storage.md)."""

import json
import os
import re
from pathlib import Path

ID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
MAX_TEXT_BYTES = 8192


class StateError(Exception):
    pass


def utf8_len(s):
    """Length of s in UTF-8 bytes; None if s cannot be encoded (lone surrogate)."""
    try:
        return len(s.encode("utf-8"))
    except UnicodeEncodeError:
        return None


def _is_string(v, non_empty=True):
    return isinstance(v, str) and (v != "" or not non_empty) and utf8_len(v) is not None


def _reject_constant(name):
    raise ValueError("not JSON: " + name)


def validate(data):
    """Validate decoded JSON; return (name, outbox) or raise StateError."""
    if not isinstance(data, dict):
        raise StateError("top level is not an object")
    if "version" not in data:
        raise StateError("version missing")
    version = data["version"]
    if not ((type(version) is int and version == 1)
            or (type(version) is float and version == 1.0)):
        raise StateError("version is not the number 1")
    if "name" not in data:
        raise StateError("name missing")
    name = data["name"]
    if name is not None and not _is_string(name):
        raise StateError("name is not null or a non-empty string")
    if "outbox" not in data or not isinstance(data["outbox"], list):
        raise StateError("outbox missing or not an array")
    entries = data["outbox"]
    if name is None and entries:
        raise StateError("outbox not empty while name is null")
    outbox = []
    ids = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise StateError("outbox entry is not an object")
        msg_id, to, text = entry.get("id"), entry.get("to"), entry.get("text")
        if not isinstance(msg_id, str) or not ID_RE.fullmatch(msg_id):
            raise StateError("outbox entry has a bad id")
        if not _is_string(to):
            raise StateError("outbox entry has a bad to")
        if not _is_string(text) or utf8_len(text) > MAX_TEXT_BYTES:
            raise StateError("outbox entry has a bad text")
        if msg_id in ids:
            raise StateError("duplicate outbox id")
        ids.add(msg_id)
        outbox.append({"id": msg_id, "to": to, "text": text})
    return name, outbox


def parse_state(raw):
    """Parse the bytes of a state file; return (name, outbox) or raise StateError."""
    if raw.startswith(b"\xef\xbb\xbf"):
        raise StateError("file starts with a byte order mark")
    try:
        text = raw.decode("utf-8")
        data = json.loads(text, parse_constant=_reject_constant)
    except (UnicodeDecodeError, ValueError) as exc:
        raise StateError("not UTF-8 JSON: %s" % exc)
    return validate(data)


def load(data_dir):
    """Return (name, outbox); raise StateError if the file exists but is unusable."""
    path = Path(data_dir) / "state.json"
    try:
        raw = path.read_bytes()
    except (FileNotFoundError, NotADirectoryError):
        return None, []
    except OSError as exc:
        raise StateError("cannot read %s: %s" % (path, exc))
    return parse_state(raw)


def save(data_dir, name, outbox):
    """Write the state atomically. Raises OSError (or ValueError) on failure."""
    directory = Path(data_dir)
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
