# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""Entry point: parse arguments, run the client."""

import asyncio
import os
import sys

from msgclient.cli import USAGE, ArgError, parse_args
from msgclient.client import Client


def main(argv):
    try:
        opts = parse_args(argv)
    except ArgError as e:
        sys.stderr.write("error: %s\n%s\n" % (e, USAGE))
        sys.stderr.flush()
        return 2
    sys.stdin.reconfigure(encoding="utf-8", errors="replace", newline=None)
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    client = Client(opts["server"], opts["data_dir"], opts["machine"])
    asyncio.run(client.run())
    return 0


if __name__ == "__main__":
    code = main(sys.argv[1:])
    sys.stdout.flush()
    sys.stderr.flush()
    # The stdin reader is a daemon thread that may still be blocked in readline();
    # exiting directly avoids interpreter-shutdown contention on the stdin lock.
    os._exit(code)
