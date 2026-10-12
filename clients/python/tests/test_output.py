# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
import unittest

from msgclient.output import Formatter, escape

ID = "0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11"


class EscapeTest(unittest.TestCase):
    def test_escape(self):
        self.assertEqual(escape("a\\nb"), "a\\\\nb")
        self.assertEqual(escape("a\nb\rc\td"), "a\\nb\\rc\\td")
        self.assertEqual(escape("x\ud800y"), "x�y")
        self.assertEqual(escape("\udfff"), "�")
        self.assertEqual(escape("héllo 👋 a b"), "héllo 👋 a b")


class MachineTest(unittest.TestCase):
    f = Formatter(True)

    def test_lines(self):
        f = self.f
        self.assertEqual(f.logged_in("alice"), "LOGGED_IN name=alice")
        self.assertEqual(f.queued(ID, "bob", "x"), f"QUEUED id={ID} to=bob")
        self.assertEqual(f.sent(ID, 3, "bob"), f"SENT id={ID} seq=3 to=bob")
        self.assertEqual(
            f.recv(2, ID, "bob", "a\tb\ud800"), f"RECV seq=2 id={ID} from=bob text=a\\tb�"
        )
        self.assertEqual(f.error("usage", "usage: /quit"), "ERROR code=usage message=usage: /quit")
        self.assertEqual(
            f.error("invalid_name", "bad\nname", ID),
            f"ERROR code=invalid_name ref={ID} message=bad\\nname",
        )
        self.assertEqual(f.offline(), "OFFLINE")
        self.assertEqual(f.disconnected(), "DISCONNECTED")
        self.assertEqual(f.bye(), "BYE")


class FriendlyTest(unittest.TestCase):
    f = Formatter(False)

    def test_lines(self):
        f = self.f
        self.assertEqual(f.logged_in("alice"), "Logged in as alice")
        self.assertEqual(f.queued(ID, "bob", "tab\there"), "[queued] to bob: tab\\there")
        self.assertEqual(f.sent(ID, 3, "bob"), "[sent]   to bob (#3)")
        self.assertEqual(f.recv(2, ID, "bob", "x\\y\ud800"), "[bob] x\\\\y�")
        self.assertEqual(f.error("c", "m\r", ID), "Error: m\\r")
        self.assertEqual(f.error("c", "m"), "Error: m")
        self.assertEqual(f.offline(), "You are offline. Messages will be queued.")
        self.assertEqual(f.disconnected(), "Disconnected. Type /online to reconnect.")
        self.assertEqual(f.bye(), "Bye.")


if __name__ == "__main__":
    unittest.main()
