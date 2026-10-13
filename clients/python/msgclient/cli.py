# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""Argument parsing and stdin command parsing (spec/core/30-cli.md)."""

DEFAULT_SERVER = "ws://127.0.0.1:8765"
DEFAULT_DATA_DIR = ".msgdata"

USAGE = "usage: python main.py [--server <url>] [--data-dir <dir>] [--machine]"


class ArgError(Exception):
    pass


def parse_args(argv):
    """Return dict with server, data_dir, machine. Raise ArgError on any error."""
    values = {}
    machine = False
    seen = set()
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--machine":
            if "--machine" in seen:
                raise ArgError("--machine given more than once")
            seen.add("--machine")
            machine = True
            i += 1
            continue
        matched = None
        for opt in ("--server", "--data-dir"):
            if arg == opt or arg.startswith(opt + "="):
                matched = opt
                break
        if matched is None:
            raise ArgError("unknown argument: " + arg)
        if matched in seen:
            raise ArgError(matched + " given more than once")
        seen.add(matched)
        if arg == matched:
            if i + 1 >= len(argv):
                raise ArgError(matched + " needs a value")
            value = argv[i + 1]
            i += 2
        else:
            value = arg[len(matched) + 1:]
            i += 1
        if value == "":
            raise ArgError(matched + " needs a non-empty value")
        values[matched] = value
    return {
        "server": values.get("--server", DEFAULT_SERVER),
        "data_dir": values.get("--data-dir", DEFAULT_DATA_DIR),
        "machine": machine,
    }


USAGE_MESSAGES = {
    "/login": "usage: /login <name>",
    "/send": "usage: /send <user> <text>",
    "/online": "usage: /online",
    "/offline": "usage: /offline",
    "/quit": "usage: /quit",
}


def parse_command(line):
    """Parse one input line (line ending already removed).

    Returns one of:
      ("empty",), ("online",), ("offline",), ("quit",), ("login", name),
      ("send", to, text), ("usage", message), ("unknown",)
    """
    if line == "":
        return ("empty",)
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
        idx = rest.find(" ")
        if idx > 0:
            to = rest[:idx]
            text = rest[idx + 1:]
            if text != "":
                return ("send", to, text)
    for cmd, message in USAGE_MESSAGES.items():
        if line == cmd or line.startswith(cmd + " "):
            return ("usage", message)
    return ("unknown",)
