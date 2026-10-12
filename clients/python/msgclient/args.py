# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""Command-line argument parsing (spec/core/30-cli.md, Invocation)."""

DEFAULT_SERVER = "ws://127.0.0.1:8765"
DEFAULT_DATA_DIR = ".msgdata"

USAGE = "usage: python main.py [--server <url>] [--data-dir <dir>] [--machine]"


class ArgError(Exception):
    pass


def parse_args(argv):
    """Return a dict with keys server, data_dir, machine; raise ArgError on any error."""
    seen = {}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--machine":
            key, value = "machine", True
        elif arg in ("--server", "--data-dir"):
            if i + 1 >= len(argv):
                raise ArgError("missing value for " + arg)
            key, value = arg[2:], argv[i + 1]
            i += 1
        elif arg.startswith("--server=") or arg.startswith("--data-dir="):
            key, value = arg[2:].split("=", 1)
        else:
            raise ArgError("unknown argument: " + arg)
        if value == "":
            raise ArgError("empty value for --" + key)
        if key in seen:
            raise ArgError("repeated option: --" + key)
        seen[key] = value
        i += 1
    return {
        "server": seen.get("server", DEFAULT_SERVER),
        "data_dir": seen.get("data-dir", DEFAULT_DATA_DIR),
        "machine": bool(seen.get("machine", False)),
    }
