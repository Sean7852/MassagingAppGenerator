# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
import unittest

from msgclient.output import escape, format_line

ID = "0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11"


class EscapeTest(unittest.TestCase):
    def test_escape(self):
        self.assertEqual(escape("a\\nb"), "a\\\\nb")
        self.assertEqual(escape("a\nb\rc\td"), "a\\nb\\rc\\td")
        self.assertEqual(escape("x\ud800y"), "x�y")
        self.assertEqual(escape("héllo 👋 a b"), "héllo 👋 a b")


class FormatTest(unittest.TestCase):
    def both(self, event, **f):
        return format_line(True, event, **f), format_line(False, event, **f)

    def test_lines(self):
        self.assertEqual(self.both("LOGGED_IN", name="alice"),
                         ("LOGGED_IN name=alice", "Logged in as alice"))
        self.assertEqual(self.both("QUEUED", id=ID, to="bob", text="a\tb"),
                         (f"QUEUED id={ID} to=bob", "[queued] to bob: a\\tb"))
        self.assertEqual(self.both("SENT", id=ID, seq=3, to="bob"),
                         (f"SENT id={ID} seq=3 to=bob", "[sent]   to bob (#3)"))
        self.assertEqual(self.both("RECV", seq=2, id=ID, from_="bob", text="hi\n\ud800"),
                         (f"RECV seq=2 id={ID} from=bob text=hi\\n�", "[bob] hi\\n�"))
        self.assertEqual(self.both("READ", msg_id=ID, msg_seq=4, by="bob"),
                         (f"READ id={ID} seq=4 by=bob", "[read]   by bob (#4)"))
        self.assertEqual(self.both("ERROR", code="x", message="m\\1"),
                         ("ERROR code=x message=m\\\\1", "Error: m\\\\1"))
        self.assertEqual(self.both("ERROR", code="x", message="m", ref=ID),
                         (f"ERROR code=x ref={ID} message=m", "Error: m"))
        self.assertEqual(self.both("OFFLINE"),
                         ("OFFLINE", "You are offline. Messages will be queued."))
        self.assertEqual(self.both("DISCONNECTED"),
                         ("DISCONNECTED", "Disconnected. Type /online to reconnect."))
        self.assertEqual(self.both("BYE"), ("BYE", "Bye."))


if __name__ == "__main__":
    unittest.main()
