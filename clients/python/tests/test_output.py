# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
import unittest

from msgclient import output


class EscapeTest(unittest.TestCase):
    def test_escape(self):
        self.assertEqual(output.escape("plain text"), "plain text")
        self.assertEqual(output.escape("a\\b"), "a\\\\b")
        self.assertEqual(output.escape("a\nb"), "a\\nb")
        self.assertEqual(output.escape("a\rb"), "a\\rb")
        self.assertEqual(output.escape("a\tb"), "a\\tb")
        self.assertEqual(output.escape("a\\nb"), "a\\\\nb")
        self.assertEqual(output.escape("héllo 你好 👋"), "héllo 你好 👋")

    def test_lines(self):
        self.assertEqual(output.logged_in("alice"), "LOGGED_IN name=alice")
        self.assertEqual(output.sent("x", 7, "bob"), "SENT id=x seq=7 to=bob")
        self.assertEqual(output.recv(3, "x", "bob", "a\tb"), "RECV seq=3 id=x from=bob text=a\\tb")
        self.assertEqual(output.error("c", "m\n"), "ERROR code=c message=m\\n")
        self.assertEqual(output.error("c", "m", "r"), "ERROR code=c ref=r message=m")


if __name__ == "__main__":
    unittest.main()
