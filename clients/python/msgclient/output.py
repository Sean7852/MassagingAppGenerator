# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""Output lines and escaping (spec/core/30-cli.md, spec/extensions/10-read-receipts.md)."""

import re
import sys

_SURROGATE = re.compile("[\ud800-\udfff]")


def clean(s):
    """Replace lone surrogates with U+FFFD (they cannot be written as UTF-8)."""
    return _SURROGATE.sub("\ufffd", s)


def escape(s):
    s = s.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    return clean(s)


def format_line(machine, event, **f):
    """Return the output line (without newline) for one event."""
    if event == "LOGGED_IN":
        name = clean(f["name"])
        return f"LOGGED_IN name={name}" if machine else f"Logged in as {name}"
    if event == "QUEUED":
        if machine:
            return f"QUEUED id={f['id']} to={clean(f['to'])}"
        return f"[queued] to {clean(f['to'])}: {escape(f['text'])}"
    if event == "SENT":
        if machine:
            return f"SENT id={f['id']} seq={f['seq']} to={clean(f['to'])}"
        return f"[sent]   to {clean(f['to'])} (#{f['seq']})"
    if event == "RECV":
        if machine:
            return (f"RECV seq={f['seq']} id={clean(f['id'])} from={clean(f['from_'])} "
                    f"text={escape(f['text'])}")
        return f"[{clean(f['from_'])}] {escape(f['text'])}"
    if event == "READ":
        if machine:
            return f"READ id={clean(f['msg_id'])} seq={f['msg_seq']} by={clean(f['by'])}"
        return f"[read]   by {clean(f['by'])} (#{f['msg_seq']})"
    if event == "ERROR":
        message = escape(f["message"])
        if not machine:
            return f"Error: {message}"
        ref = f.get("ref")
        if ref is None:
            return f"ERROR code={clean(f['code'])} message={message}"
        return f"ERROR code={clean(f['code'])} ref={clean(ref)} message={message}"
    if event == "OFFLINE":
        return "OFFLINE" if machine else "You are offline. Messages will be queued."
    if event == "DISCONNECTED":
        return "DISCONNECTED" if machine else "Disconnected. Type /online to reconnect."
    if event == "BYE":
        return "BYE" if machine else "Bye."
    raise ValueError("unknown event " + event)


def write_line(line):
    """The only function that writes to stdout."""
    sys.stdout.write(line + "\n")
    sys.stdout.flush()
