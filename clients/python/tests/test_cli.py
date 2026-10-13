# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
import unittest

from msgclient.cli import ArgError, parse_args, parse_command


class CommandParsingTest(unittest.TestCase):
    def test_exact_commands(self):
        self.assertEqual(parse_command("/online"), ("online",))
        self.assertEqual(parse_command("/offline"), ("offline",))
        self.assertEqual(parse_command("/quit"), ("quit",))

    def test_empty(self):
        self.assertEqual(parse_command(""), ("empty",))

    def test_login(self):
        self.assertEqual(parse_command("/login alice"), ("login", "alice"))
        self.assertEqual(parse_command("/login Al!ce"), ("login", "Al!ce"))
        self.assertEqual(parse_command("/login alice bob"), ("usage", "usage: /login <name>"))
        self.assertEqual(parse_command("/login"), ("usage", "usage: /login <name>"))
        self.assertEqual(parse_command("/login "), ("usage", "usage: /login <name>"))
        self.assertEqual(parse_command("/login  alice"), ("usage", "usage: /login <name>"))

    def test_send(self):
        self.assertEqual(parse_command("/send bob hi there"), ("send", "bob", "hi there"))
        self.assertEqual(parse_command("/send bob  hi"), ("send", "bob", " hi"))
        self.assertEqual(parse_command("/send bob hi "), ("send", "bob", "hi "))
        self.assertEqual(parse_command("/send bob a b"), ("send", "bob", "a b"))
        self.assertEqual(parse_command("/send bob a\tb"), ("send", "bob", "a\tb"))
        usage = ("usage", "usage: /send <user> <text>")
        self.assertEqual(parse_command("/send bob"), usage)
        self.assertEqual(parse_command("/send bob "), usage)
        self.assertEqual(parse_command("/send  bob hi"), usage)
        self.assertEqual(parse_command("/send"), usage)
        self.assertEqual(parse_command("/send "), usage)

    def test_usage_other(self):
        self.assertEqual(parse_command("/online now"), ("usage", "usage: /online"))
        self.assertEqual(parse_command("/online "), ("usage", "usage: /online"))
        self.assertEqual(parse_command("/offline please"), ("usage", "usage: /offline"))
        self.assertEqual(parse_command("/quit now"), ("usage", "usage: /quit"))

    def test_unknown(self):
        for line in ("hello", "/sendx bob hi", "/Online", " /online", "/onlinex", "/"):
            self.assertEqual(parse_command(line), ("unknown",), line)


class ArgParsingTest(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(parse_args([]), {"server": "ws://127.0.0.1:8765",
                                          "data_dir": ".msgdata", "machine": False})

    def test_values(self):
        o = parse_args(["--machine", "--server", "ws://x:1", "--data-dir=d"])
        self.assertEqual(o, {"server": "ws://x:1", "data_dir": "d", "machine": True})
        o = parse_args(["--data-dir", "e", "--server=ws://y"])
        self.assertEqual(o["data_dir"], "e")
        self.assertEqual(o["server"], "ws://y")

    def test_errors(self):
        bad = [
            ["--unknown"], ["-h"], ["--help"], ["--serv", "ws://x"], ["--machine", "--machine"],
            ["--server", "a", "--server", "b"], ["--server"], ["--server="], ["--server", ""],
            ["--data-dir"], ["--data-dir="], ["positional"], ["--machine=1"],
            ["--data-dir", "a", "--data-dir=b"],
        ]
        for argv in bad:
            with self.assertRaises(ArgError, msg=str(argv)):
                parse_args(argv)


if __name__ == "__main__":
    unittest.main()
