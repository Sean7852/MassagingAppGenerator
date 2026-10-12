# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""Output lines and escaping (spec/core/30-cli.md, Output)."""
import sys


def escape(s):
    return (
        s.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def write_line(line):
    """The only function that writes to stdout."""
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def logged_in(name):
    return f"LOGGED_IN name={name}"


def sent(msg_id, seq, to):
    return f"SENT id={msg_id} seq={seq} to={to}"


def recv(seq, msg_id, sender, text):
    return f"RECV seq={seq} id={msg_id} from={sender} text={escape(text)}"


def error(code, message, ref=None):
    if ref is None:
        return f"ERROR code={code} message={escape(message)}"
    return f"ERROR code={code} ref={ref} message={escape(message)}"


DISCONNECTED = "DISCONNECTED"
BYE = "BYE"

USAGE_MESSAGES = {
    "/login": "usage: /login <name>",
    "/send": "usage: /send <user> <text>",
    "/quit": "usage: /quit",
}
MSG_UNKNOWN_COMMAND = "unknown command"
MSG_ALREADY_LOGGED_IN = "already logged in or connecting"
MSG_NOT_LOGGED_IN = "log in first with /login <name>"
MSG_NOT_SENT = "connection lost before the server acknowledged the message"


def msg_connect_failed(url):
    return f"cannot connect to {url}"
