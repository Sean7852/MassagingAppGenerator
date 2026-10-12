# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
import unittest

from msgclient.output import Formatter, escape

ID = "0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11"


class EscapeTest(unittest.TestCase):
    def test_escapes(self):
        self.assertEqual(escape("a\\b\nc\rd\te"), "a\\\\b\\nc\\rd\\te")
        self.assertEqual(escape("a\\nb"), "a\\\\nb")
        self.assertEqual(escape("héllo 👋 a b"), "héllo 👋 a b")

    def test_lone_surrogate(self):
        self.assertEqual(escape("x\ud800y\udfff"), "x�y�")


class MachineLinesTest(unittest.TestCase):
    f = Formatter(True)

    def test_lines(self):
        f = self.f
        self.assertEqual(f.logged_in("alice"), "LOGGED_IN name=alice")
        self.assertEqual(f.queued(ID, "bob", "x"), "QUEUED id=%s to=bob" % ID)
        self.assertEqual(f.sent(ID, 3, "bob"), "SENT id=%s seq=3 to=bob" % ID)
        self.assertEqual(f.recv(2, ID, "bob", "a\tb"),
                         "RECV seq=2 id=%s from=bob text=a\\tb" % ID)
        self.assertEqual(f.recv(2, ID, "bob", "\ud800"),
                         "RECV seq=2 id=%s from=bob text=�" % ID)
        self.assertEqual(f.read(ID, 3, "bob"), "READ id=%s seq=3 by=bob" % ID)
        self.assertEqual(f.error("usage", "usage: /quit"), "ERROR code=usage message=usage: /quit")
        self.assertEqual(f.error("invalid_name", "a\nb", ID),
                         "ERROR code=invalid_name ref=%s message=a\\nb" % ID)
        self.assertEqual(f.offline(), "OFFLINE")
        self.assertEqual(f.disconnected(), "DISCONNECTED")
        self.assertEqual(f.bye(), "BYE")


class FriendlyLinesTest(unittest.TestCase):
    f = Formatter(False)

    def test_lines(self):
        f = self.f
        self.assertEqual(f.logged_in("alice"), "Logged in as alice")
        self.assertEqual(f.queued(ID, "bob", "tab\there"), "[queued] to bob: tab\\there")
        self.assertEqual(f.sent(ID, 1, "bob"), "[sent]   to bob (#1)")
        self.assertEqual(f.recv(2, ID, "bob", "hi\\"), "[bob] hi\\\\")
        self.assertEqual(f.recv(2, ID, "bob", "\udc00"), "[bob] �")
        self.assertEqual(f.read(ID, 3, "bob"), "[read]   by bob (#3)")
        self.assertEqual(f.error("x", "m\r", ID), "Error: m\\r")
        self.assertEqual(f.error("x", "m"), "Error: m")
        self.assertEqual(f.offline(), "You are offline. Messages will be queued.")
        self.assertEqual(f.disconnected(), "Disconnected. Type /online to reconnect.")
        self.assertEqual(f.bye(), "Bye.")


if __name__ == "__main__":
    unittest.main()
