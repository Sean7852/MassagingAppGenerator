# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
import json
import pathlib
import tempfile
import unittest

from msgclient.storage import StateError, load_state, parse_state, save_state

ID1 = "0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11"
ID2 = "5d2e8a90-7c1b-4f3e-8d6a-2b9c4e1f0a77"


def enc(obj):
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def good(**over):
    obj = {"version": 1, "name": "alice", "outbox": [{"id": ID1, "to": "bob", "text": "hi"}]}
    obj.update(over)
    return obj


class ParseStateTest(unittest.TestCase):
    def assertInvalid(self, data):
        with self.assertRaises(StateError):
            parse_state(data)

    def test_valid(self):
        self.assertEqual(parse_state(enc(good())), ("alice", [{"id": ID1, "to": "bob", "text": "hi"}]))
        self.assertEqual(parse_state(enc({"version": 1, "name": None, "outbox": []})), (None, []))
        self.assertEqual(parse_state(enc(good(version=1.0)))[0], "alice")

    def test_extra_fields_ignored(self):
        obj = good(extra=1)
        obj["outbox"][0]["more"] = True
        self.assertEqual(parse_state(enc(obj))[1], [{"id": ID1, "to": "bob", "text": "hi"}])

    def test_rule1_utf8_json_object(self):
        self.assertInvalid(b"\xef\xbb\xbf" + enc(good()))
        self.assertInvalid(b"\xff\xfe")
        self.assertInvalid(b"not json")
        self.assertInvalid(enc([1, 2]))

    def test_rule2_version(self):
        obj = good()
        del obj["version"]
        self.assertInvalid(enc(obj))
        for v in [True, "1", 2, 1.5, None]:
            self.assertInvalid(enc(good(version=v)))

    def test_rule3_name(self):
        obj = good()
        del obj["name"]
        self.assertInvalid(enc(obj))
        for v in ["", 5, False, []]:
            self.assertInvalid(enc(good(name=v)))

    def test_rule4_outbox(self):
        obj = good()
        del obj["outbox"]
        self.assertInvalid(enc(obj))
        self.assertInvalid(enc(good(outbox={})))
        self.assertInvalid(enc(good(name=None)))

    def test_rule5_entries(self):
        long_ok = "é" * 4096
        self.assertEqual(parse_state(enc(good(outbox=[{"id": ID1, "to": "b", "text": long_ok}])))[0], "alice")
        bad_entries = [
            "x",
            {"to": "bob", "text": "hi"},
            {"id": ID1.upper(), "to": "bob", "text": "hi"},
            {"id": "not-a-uuid", "to": "bob", "text": "hi"},
            {"id": 5, "to": "bob", "text": "hi"},
            {"id": ID1, "to": "", "text": "hi"},
            {"id": ID1, "text": "hi"},
            {"id": ID1, "to": "bob", "text": ""},
            {"id": ID1, "to": "bob"},
            {"id": ID1, "to": "bob", "text": 3},
            {"id": ID1, "to": "bob", "text": "x" * 8193},
            {"id": ID1, "to": "bob", "text": long_ok + "x"},
        ]
        for entry in bad_entries:
            self.assertInvalid(enc(good(outbox=[entry])))

    def test_rule6_unique_ids(self):
        e = {"id": ID1, "to": "bob", "text": "hi"}
        self.assertInvalid(enc(good(outbox=[e, dict(e)])))
        e2 = {"id": ID2, "to": "bob", "text": "hi"}
        self.assertEqual(len(parse_state(enc(good(outbox=[e, e2])))[1]), 2)


class SaveLoadTest(unittest.TestCase):
    def test_missing_file_and_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp) / "a" / "b"
            self.assertEqual(load_state(d), (None, []))
            self.assertFalse(d.exists())
            outbox = [{"id": ID1, "to": "bob", "text": "héllo\n"}]
            save_state(d, "alice", outbox)
            self.assertEqual(load_state(d), ("alice", outbox))
            self.assertFalse((d / "state.json.tmp").exists())
            (d / "state.json.tmp").write_text("garbage")
            self.assertEqual(load_state(d), ("alice", outbox))

    def test_invalid_file_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "state.json"
            p.write_bytes(b"{bad")
            with self.assertRaises(StateError):
                load_state(tmp)
            self.assertEqual(p.read_bytes(), b"{bad")


if __name__ == "__main__":
    unittest.main()
