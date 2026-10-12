# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""Output lines, in machine and friendly modes (30-cli.md)."""
import re
import sys

_LONE_SURROGATE = re.compile("[\ud800-\udfff]")


def escape(s):
    s = _LONE_SURROGATE.sub("�", s)
    return (
        s.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


class Formatter:
    """Builds output lines (without the trailing newline)."""

    def __init__(self, machine):
        self.machine = machine

    def logged_in(self, name):
        if self.machine:
            return f"LOGGED_IN name={name}"
        return f"Logged in as {name}"

    def queued(self, id_, to, text):
        if self.machine:
            return f"QUEUED id={id_} to={to}"
        return f"[queued] to {to}: {escape(text)}"

    def sent(self, id_, seq, to):
        if self.machine:
            return f"SENT id={id_} seq={seq} to={to}"
        return f"[sent]   to {to} (#{seq})"

    def recv(self, seq, id_, from_, text):
        if self.machine:
            return f"RECV seq={seq} id={id_} from={from_} text={escape(text)}"
        return f"[{from_}] {escape(text)}"

    def error(self, code, message, ref=None):
        if self.machine:
            if ref is None:
                return f"ERROR code={code} message={escape(message)}"
            return f"ERROR code={code} ref={ref} message={escape(message)}"
        return f"Error: {escape(message)}"

    def offline(self):
        return "OFFLINE" if self.machine else "You are offline. Messages will be queued."

    def disconnected(self):
        return "DISCONNECTED" if self.machine else "Disconnected. Type /online to reconnect."

    def bye(self):
        return "BYE" if self.machine else "Bye."


def write_line(line):
    """The only function that writes to stdout."""
    sys.stdout.write(line + "\n")
    sys.stdout.flush()
