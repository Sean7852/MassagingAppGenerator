# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""Output lines in machine and friendly mode (spec/core/30-cli.md, extension 10)."""

import re
import sys

_SURROGATE = re.compile("[\ud800-\udfff]")


def fix_surrogates(s):
    return _SURROGATE.sub("\ufffd", s)


def escape(s):
    s = fix_surrogates(s)
    return (s.replace("\\", "\\\\").replace("\n", "\\n")
            .replace("\r", "\\r").replace("\t", "\\t"))


def write_line(line):
    """The only function that writes to stdout."""
    sys.stdout.write(fix_surrogates(line) + "\n")
    sys.stdout.flush()


class Formatter:
    """Builds the text of each output line, without the line ending."""

    def __init__(self, machine):
        self.machine = machine

    def logged_in(self, name):
        return "LOGGED_IN name=" + name if self.machine else "Logged in as " + name

    def queued(self, msg_id, to, text):
        if self.machine:
            return "QUEUED id=%s to=%s" % (msg_id, to)
        return "[queued] to %s: %s" % (to, escape(text))

    def sent(self, msg_id, seq, to):
        if self.machine:
            return "SENT id=%s seq=%d to=%s" % (msg_id, seq, to)
        return "[sent]   to %s (#%d)" % (to, seq)

    def recv(self, seq, msg_id, sender, text):
        if self.machine:
            return "RECV seq=%d id=%s from=%s text=%s" % (seq, msg_id, sender, escape(text))
        return "[%s] %s" % (sender, escape(text))

    def read(self, msg_id, msg_seq, by):
        if self.machine:
            return "READ id=%s seq=%d by=%s" % (msg_id, msg_seq, by)
        return "[read]   by %s (#%d)" % (by, msg_seq)

    def error(self, code, message, ref=None):
        if self.machine:
            if ref is None:
                return "ERROR code=%s message=%s" % (code, escape(message))
            return "ERROR code=%s ref=%s message=%s" % (code, ref, escape(message))
        return "Error: " + escape(message)

    def offline(self):
        return "OFFLINE" if self.machine else "You are offline. Messages will be queued."

    def disconnected(self):
        return "DISCONNECTED" if self.machine else "Disconnected. Type /online to reconnect."

    def bye(self):
        return "BYE" if self.machine else "Bye."
