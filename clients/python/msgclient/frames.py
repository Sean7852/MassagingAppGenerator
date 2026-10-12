# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""Decoding and validating server frames (10-protocol.md, 90-defaults.md rule 2)."""
import json

MAX_SEQ = 2**53 - 1


def encode(frame):
    return json.dumps(frame, separators=(",", ":"), ensure_ascii=False)


def decode(raw):
    """Return the frame as a dict with a string `type`, or None if broken."""
    try:
        obj = json.loads(raw)
    except (ValueError, RecursionError):
        return None
    if not isinstance(obj, dict) or not isinstance(obj.get("type"), str):
        return None
    return obj


def seq_value(v):
    """Return the seq as an int, or None if it breaks the rules."""
    if type(v) is int:
        n = v
    elif type(v) is float:
        if not v.is_integer():
            return None
        n = int(v)
    else:
        return None
    if 1 <= n <= MAX_SEQ:
        return n
    return None


def _strings(frame, *keys):
    return all(isinstance(frame.get(k), str) for k in keys)


def login_ok(frame):
    """Return the name, or None if broken."""
    return frame["name"] if _strings(frame, "name") else None


def ack(frame):
    """Return (id, seq), or None if broken."""
    if not _strings(frame, "id"):
        return None
    seq = seq_value(frame.get("seq"))
    if seq is None:
        return None
    return frame["id"], seq


def deliver(frame):
    """Return (seq, id, from, text), or None if broken. `to` is not checked."""
    if not _strings(frame, "id", "from", "text"):
        return None
    seq = seq_value(frame.get("seq"))
    if seq is None:
        return None
    return seq, frame["id"], frame["from"], frame["text"]


def error(frame):
    """Return (code, message, ref) with ref None when absent, or None if broken."""
    if not _strings(frame, "code", "message"):
        return None
    ref = frame.get("ref")
    if ref is not None and not isinstance(ref, str):
        return None
    return frame["code"], frame["message"], ref
