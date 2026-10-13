# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""Frame encoding and validation of server frames (spec/core/10-protocol.md, 90-defaults.md)."""

import json

MAX_SEQ = 2 ** 53 - 1


def encode(frame):
    """Compact JSON for one frame."""
    text = json.dumps(frame, separators=(",", ":"), ensure_ascii=False)
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        text = json.dumps(frame, separators=(",", ":"), ensure_ascii=True)
    return text


def seq_value(v):
    """Return v as an int if it is a valid seq (whole number 1..2^53-1), else None."""
    if type(v) is int:
        return v if 1 <= v <= MAX_SEQ else None
    if type(v) is float:
        if v == v and v.is_integer() and 1 <= v <= MAX_SEQ:
            return int(v)
    return None


def parse_frame(raw):
    """Parse and validate a server frame.

    Returns a dict with normalized fields and key "type", or None if the frame must be
    ignored (binary, not JSON, not an object, unknown type, or broken).
    """
    if not isinstance(raw, str):
        return None
    try:
        obj = json.loads(raw)
    except (ValueError, RecursionError):
        return None
    if not isinstance(obj, dict):
        return None
    t = obj.get("type")
    if not isinstance(t, str):
        return None
    if t == "login_ok":
        if not isinstance(obj.get("name"), str):
            return None
        return {"type": t, "name": obj["name"]}
    if t == "ack":
        seq = seq_value(obj.get("seq"))
        if seq is None or not isinstance(obj.get("id"), str):
            return None
        return {"type": t, "id": obj["id"], "seq": seq}
    if t == "deliver":
        seq = seq_value(obj.get("seq"))
        if seq is None:
            return None
        for k in ("id", "from", "text"):
            if not isinstance(obj.get(k), str):
                return None
        return {"type": t, "seq": seq, "id": obj["id"], "from": obj["from"], "text": obj["text"]}
    if t == "error":
        code, message, ref = obj.get("code"), obj.get("message"), obj.get("ref")
        if not isinstance(code, str) or not isinstance(message, str):
            return None
        if ref is not None and not isinstance(ref, str):
            return None
        return {"type": t, "code": code, "message": message, "ref": ref}
    if t == "receipt":
        seq = seq_value(obj.get("seq"))
        msg_seq = seq_value(obj.get("msg_seq"))
        if seq is None or msg_seq is None:
            return None
        if not isinstance(obj.get("msg_id"), str) or not isinstance(obj.get("by"), str):
            return None
        return {"type": t, "seq": seq, "msg_seq": msg_seq, "msg_id": obj["msg_id"],
                "by": obj["by"]}
    return None
