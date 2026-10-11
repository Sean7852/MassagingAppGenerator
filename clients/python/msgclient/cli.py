# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""Argument parsing and startup (spec/core/30-cli.md, Invocation)."""
import argparse
import asyncio
import sys

from .client import Client

DEFAULT_URL = "ws://127.0.0.1:8765"


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="main.py", add_help=False, allow_abbrev=False)
    parser.add_argument("--server", default=DEFAULT_URL)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    asyncio.run(Client(args.server).run())
    return 0
