# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""Stdin command parsing (spec/core/30-cli.md, Commands)."""

USAGE_MESSAGES = {
    "/login": "usage: /login <name>",
    "/send": "usage: /send <user> <text>",
    "/online": "usage: /online",
    "/offline": "usage: /offline",
    "/quit": "usage: /quit",
}


def parse_line(line):
    """Parse one input line (line ending already removed).

    Returns None for an empty line, otherwise one of:
    ("online",), ("offline",), ("quit",), ("login", name), ("send", to, text),
    ("usage", message), ("unknown",).
    """
    if line == "":
        return None
    if line == "/online":
        return ("online",)
    if line == "/offline":
        return ("offline",)
    if line == "/quit":
        return ("quit",)
    if line.startswith("/login "):
        name = line[len("/login "):]
        if name != "" and " " not in name:
            return ("login", name)
    if line.startswith("/send "):
        rest = line[len("/send "):]
        sp = rest.find(" ")
        if sp > 0 and sp + 1 < len(rest):
            return ("send", rest[:sp], rest[sp + 1:])
    for cmd, message in USAGE_MESSAGES.items():
        if line == cmd or line.startswith(cmd + " "):
            return ("usage", message)
    return ("unknown",)
