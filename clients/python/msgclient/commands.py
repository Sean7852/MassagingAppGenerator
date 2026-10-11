# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""Parsing of stdin command lines (spec/core/30-cli.md, Input)."""
import re

_LOGIN_RE = re.compile(r"/login ([^ ]+)")
_SEND_RE = re.compile(r"/send ([^ ]+) (.+)", re.DOTALL)


def parse(line):
    """Parse one line (line ending already removed).

    Returns one of:
      ("empty",)
      ("login", name)
      ("send", to, text)
      ("quit",)
      ("usage", "/login" | "/send" | "/quit")
      ("unknown",)
    """
    if line == "":
        return ("empty",)
    m = _LOGIN_RE.fullmatch(line)
    if m:
        return ("login", m.group(1))
    m = _SEND_RE.fullmatch(line)
    if m:
        return ("send", m.group(1), m.group(2))
    if line == "/quit":
        return ("quit",)
    for cmd in ("/login", "/send", "/quit"):
        if line == cmd or line.startswith(cmd + " "):
            return ("usage", cmd)
    return ("unknown",)
