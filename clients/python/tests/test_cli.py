# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
import unittest

from msgclient.cli import DEFAULT_DATA_DIR, DEFAULT_SERVER, UsageError, parse_args, parse_command


class ParseCommandTest(unittest.TestCase):
    def test_exact_commands(self):
        self.assertEqual(parse_command("/online"), ("online",))
        self.assertEqual(parse_command("/offline"), ("offline",))
        self.assertEqual(parse_command("/quit"), ("quit",))

    def test_empty(self):
        self.assertEqual(parse_command(""), ("empty",))

    def test_login(self):
        self.assertEqual(parse_command("/login alice"), ("login", "alice"))
        self.assertEqual(parse_command("/login Alice!"), ("login", "Alice!"))

    def test_login_usage(self):
        for line in ["/login", "/login ", "/login alice bob", "/login  alice", "/login alice "]:
            self.assertEqual(parse_command(line), ("usage", "usage: /login <name>"), line)

    def test_send(self):
        self.assertEqual(parse_command("/send bob hi there"), ("send", "bob", "hi there"))
        self.assertEqual(parse_command("/send bob  hi"), ("send", "bob", " hi"))
        self.assertEqual(parse_command("/send bob a b"), ("send", "bob", "a b"))
        self.assertEqual(parse_command("/send bob tab\there"), ("send", "bob", "tab\there"))
        self.assertEqual(parse_command("/send bob x "), ("send", "bob", "x "))

    def test_send_usage(self):
        for line in ["/send", "/send ", "/send bob", "/send bob ", "/send  bob hi"]:
            self.assertEqual(parse_command(line), ("usage", "usage: /send <user> <text>"), line)

    def test_other_usage(self):
        self.assertEqual(parse_command("/online now"), ("usage", "usage: /online"))
        self.assertEqual(parse_command("/online "), ("usage", "usage: /online"))
        self.assertEqual(parse_command("/offline please"), ("usage", "usage: /offline"))
        self.assertEqual(parse_command("/quit now"), ("usage", "usage: /quit"))

    def test_unknown(self):
        for line in ["hello", "/sendx bob hi", "/Online", " /online", "/onlinex", "/", "/help"]:
            self.assertEqual(parse_command(line), ("unknown",), line)


class ParseArgsTest(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(parse_args([]), (DEFAULT_SERVER, DEFAULT_DATA_DIR, False))

    def test_all_forms(self):
        self.assertEqual(
            parse_args(["--machine", "--server", "ws://x:1", "--data-dir=d"]),
            ("ws://x:1", "d", True),
        )
        self.assertEqual(
            parse_args(["--data-dir", "d", "--server=ws://y"]), ("ws://y", "d", False)
        )

    def test_errors(self):
        bad = [
            ["--unknown"],
            ["-h"],
            ["--help"],
            ["--serv", "ws://x"],
            ["--server"],
            ["--server="],
            ["--server", ""],
            ["--data-dir"],
            ["--data-dir="],
            ["--server", "a", "--server", "b"],
            ["--server=a", "--server=b"],
            ["--machine", "--machine"],
            ["--machine=1"],
            ["positional"],
            ["--data-dir", "d", "extra"],
        ]
        for argv in bad:
            with self.assertRaises(UsageError, msg=str(argv)):
                parse_args(argv)


if __name__ == "__main__":
    unittest.main()
