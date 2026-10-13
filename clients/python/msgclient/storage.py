# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""The per-user state file (spec/core/40-storage.md)."""

import json
import os
import pathlib
import re

ID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
MAX_TEXT_BYTES = 8192


class StateError(Exception):
    pass


def utf8_len(s):
    """Length in UTF-8 bytes, or None if s has no UTF-8 encoding (lone surrogate)."""
    try:
        return len(s.encode("utf-8"))
    except UnicodeEncodeError:
        return None


def _reject_constant(name):
    raise ValueError("not JSON: " + name)


def validate_state(data):
    """Validate the bytes of a state file. Return the outbox list or raise StateError."""
    if data.startswith(b"\xef\xbb\xbf"):
        raise StateError("file starts with a byte order mark")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise StateError("not UTF-8: %s" % e)
    try:
        obj = json.loads(text, parse_constant=_reject_constant)
    except ValueError as e:
        raise StateError("not JSON: %s" % e)
    if not isinstance(obj, dict):
        raise StateError("top level is not an object")
    if "version" not in obj:
        raise StateError("version missing")
    version = obj["version"]
    if not ((type(version) is int and version == 2)
            or (type(version) is float and version == 2.0)):
        raise StateError("version is not 2")
    if "outbox" not in obj or not isinstance(obj["outbox"], list):
        raise StateError("outbox missing or not an array")
    outbox = []
    ids = set()
    for entry in obj["outbox"]:
        if not isinstance(entry, dict):
            raise StateError("outbox entry is not an object")
        mid, to, txt = entry.get("id"), entry.get("to"), entry.get("text")
        if not isinstance(mid, str) or not ID_RE.fullmatch(mid):
            raise StateError("outbox entry has a bad id")
        if not isinstance(to, str) or to == "":
            raise StateError("outbox entry has a bad to")
        if not isinstance(txt, str) or txt == "":
            raise StateError("outbox entry has a bad text")
        n = utf8_len(txt)
        if n is None or n > MAX_TEXT_BYTES:
            raise StateError("outbox entry text is too long or not UTF-8")
        if mid in ids:
            raise StateError("duplicate id in outbox")
        ids.add(mid)
        outbox.append({"id": mid, "to": to, "text": txt})
    return outbox


def state_path(data_dir, name):
    return pathlib.Path(data_dir) / name / "state.json"


def load_outbox(data_dir, name):
    """Return the saved outbox (empty if no file). Raise StateError if unreadable/invalid."""
    path = state_path(data_dir, name)
    if not path.exists():
        return []
    try:
        data = path.read_bytes()
    except OSError as e:
        raise StateError("cannot read %s: %s" % (path, e))
    try:
        return validate_state(data)
    except StateError as e:
        raise StateError("%s: %s" % (path, e))


def save_outbox(data_dir, name, outbox):
    """Write the state atomically. Raises OSError (or similar) on failure."""
    path = state_path(data_dir, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("state.json.tmp")
    state = {
        "version": 2,
        "outbox": [{"id": m["id"], "to": m["to"], "text": m["text"]} for m in outbox],
    }
    try:
        content = json.dumps(state, ensure_ascii=False)
        content.encode("utf-8")
    except UnicodeEncodeError:
        content = json.dumps(state, ensure_ascii=True)
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
