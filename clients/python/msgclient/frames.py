# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""Decoding and checking server frames (spec/core/10-protocol.md, 90-defaults.md rule 2)."""

import json

MAX_SEQ = 2 ** 53 - 1

# Fields each known frame type needs: name -> kind ("str" or "seq").
REQUIRED = {
    "login_ok": {"name": "str"},
    "ack": {"id": "str", "seq": "seq"},
    "deliver": {"seq": "seq", "id": "str", "from": "str", "text": "str"},
    "error": {"code": "str", "message": "str"},
    "receipt": {"seq": "seq", "msg_seq": "seq", "msg_id": "str", "by": "str"},
}


def as_seq(v):
    """Return v as an int if it is a valid seq number, else None."""
    if type(v) is int:
        n = v
    elif type(v) is float and v.is_integer():
        n = int(v)
    else:
        return None
    return n if 1 <= n <= MAX_SEQ else None


def decode(raw):
    """Decode a text frame. Return a dict with checked fields, or None to ignore it.

    Unknown types are returned with only "type" set, so the caller can ignore them.
    """
    try:
        obj = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(obj, dict) or not isinstance(obj.get("type"), str):
        return None
    ftype = obj["type"]
    fields = REQUIRED.get(ftype)
    if fields is None:
        return {"type": ftype}
    frame = {"type": ftype}
    for key, kind in fields.items():
        if key not in obj:
            return None
        value = obj[key]
        if kind == "seq":
            value = as_seq(value)
            if value is None:
                return None
        elif not isinstance(value, str):
            return None
        frame[key] = value
    if ftype == "error":
        ref = obj.get("ref")
        if ref is not None and not isinstance(ref, str):
            return None
        frame["ref"] = ref
    return frame


def encode(frame):
    return json.dumps(frame, separators=(",", ":"), ensure_ascii=False)
