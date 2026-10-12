# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
import unittest

from msgclient.commands import parse


class ParseTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(parse(""), ("empty",))

    def test_login(self):
        self.assertEqual(parse("/login alice"), ("login", "alice"))
        self.assertEqual(parse("/login Alice!"), ("login", "Alice!"))

    def test_send(self):
        self.assertEqual(parse("/send bob hi"), ("send", "bob", "hi"))
        self.assertEqual(parse("/send bob  hi"), ("send", "bob", " hi"))
        self.assertEqual(parse("/send bob a b "), ("send", "bob", "a b "))
        self.assertEqual(parse("/send bob a\tb\\n"), ("send", "bob", "a\tb\\n"))

    def test_quit(self):
        self.assertEqual(parse("/quit"), ("quit",))

    def test_usage(self):
        self.assertEqual(parse("/login"), ("usage", "/login"))
        self.assertEqual(parse("/login "), ("usage", "/login"))
        self.assertEqual(parse("/login alice extra"), ("usage", "/login"))
        self.assertEqual(parse("/login  alice"), ("usage", "/login"))
        self.assertEqual(parse("/send"), ("usage", "/send"))
        self.assertEqual(parse("/send bob"), ("usage", "/send"))
        self.assertEqual(parse("/send bob "), ("usage", "/send"))
        self.assertEqual(parse("/send  bob hi"), ("usage", "/send"))
        self.assertEqual(parse("/quit now"), ("usage", "/quit"))
        self.assertEqual(parse("/quit "), ("usage", "/quit"))

    def test_unknown(self):
        for line in ("hello", "/sendx bob hi", "/loginx", "/quitx", "/login\talice", " /quit", "/QUIT"):
            self.assertEqual(parse(line), ("unknown",), line)


if __name__ == "__main__":
    unittest.main()
