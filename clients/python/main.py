# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""Entry point: python main.py [--server <url>] [--data-dir <dir>] [--machine]"""

import asyncio
import sys

from msgclient.args import USAGE, ArgError, parse_args
from msgclient import storage


def main():
    try:
        options = parse_args(sys.argv[1:])
    except ArgError as exc:
        sys.stderr.write("%s\n%s\n" % (exc, USAGE))
        sys.stderr.flush()
        return 2

    sys.stdin.reconfigure(encoding="utf-8", errors="replace", newline=None)
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")

    try:
        name, outbox = storage.load(options["data_dir"])
    except storage.StateError as exc:
        sys.stderr.write("cannot load saved state: %s\n" % exc)
        sys.stderr.flush()
        return 1

    from msgclient.client import Client

    client = Client(options["server"], options["data_dir"], options["machine"], name, outbox)
    asyncio.run(client.run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
