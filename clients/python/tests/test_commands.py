# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
import unittest

from msgclient.commands import parse_line


class CommandParsingTest(unittest.TestCase):
    def test_empty_line_is_ignored(self):
        self.assertIsNone(parse_line(""))

    def test_exact_commands(self):
        self.assertEqual(parse_line("/online"), ("online",))
        self.assertEqual(parse_line("/offline"), ("offline",))
        self.assertEqual(parse_line("/quit"), ("quit",))

    def test_login(self):
        self.assertEqual(parse_line("/login alice"), ("login", "alice"))
        self.assertEqual(parse_line("/login Alice!"), ("login", "Alice!"))

    def test_send_examples(self):
        self.assertEqual(parse_line("/send bob hi there"), ("send", "bob", "hi there"))
        self.assertEqual(parse_line("/send bob  hi"), ("send", "bob", " hi"))
        self.assertEqual(parse_line("/send bob a\tb "), ("send", "bob", "a\tb "))

    def test_send_text_with_line_separator(self):
        self.assertEqual(parse_line("/send bob a b"), ("send", "bob", "a b"))

    def test_usage_errors(self):
        cases = {
            "/send bob": "usage: /send <user> <text>",
            "/send bob ": "usage: /send <user> <text>",
            "/send  bob hi": "usage: /send <user> <text>",
            "/send": "usage: /send <user> <text>",
            "/send ": "usage: /send <user> <text>",
            "/login": "usage: /login <name>",
            "/login ": "usage: /login <name>",
            "/login alice bob": "usage: /login <name>",
            "/online now": "usage: /online",
            "/online ": "usage: /online",
            "/offline please": "usage: /offline",
            "/quit now": "usage: /quit",
        }
        for line, message in cases.items():
            with self.subTest(line=line):
                self.assertEqual(parse_line(line), ("usage", message))

    def test_unknown(self):
        for line in ["hello", "/sendx bob hi", "/Online", " /online", "/online\t", "/"]:
            with self.subTest(line=line):
                self.assertEqual(parse_line(line), ("unknown",))


if __name__ == "__main__":
    unittest.main()
