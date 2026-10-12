# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
import json
import os
import tempfile
import unittest

from msgclient import storage
from msgclient.storage import StateError, parse_state

ID1 = "0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11"
ID2 = "5d2e8a90-7c1b-4f3e-8d6a-2b9c4e1f0a77"


def raw(obj):
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def entry(i=ID1, to="bob", text="hi"):
    return {"id": i, "to": to, "text": text}


class ValidationTest(unittest.TestCase):
    def ok(self, obj):
        return parse_state(raw(obj))

    def bad(self, data):
        with self.assertRaises(StateError):
            parse_state(data if isinstance(data, bytes) else raw(data))

    def test_valid(self):
        self.assertEqual(self.ok({"version": 1, "name": None, "outbox": []}), (None, []))
        self.assertEqual(
            self.ok({"version": 1.0, "name": "alice", "outbox": [entry(), entry(ID2)],
                     "extra": 1}),
            ("alice", [entry(), entry(ID2)]))
        e = dict(entry(), more=True)
        self.assertEqual(self.ok({"version": 1, "name": "a", "outbox": [e]}), ("a", [entry()]))
        self.assertEqual(self.ok({"version": 1, "name": "a", "outbox": [entry(text="é" * 4096)]})[0],
                         "a")

    def test_rule1_utf8_json_object(self):
        self.bad(b"\xef\xbb\xbf" + raw({"version": 1, "name": None, "outbox": []}))
        self.bad(b"not json")
        self.bad(b"\xff\xfe")
        self.bad(raw([1]))
        self.bad(b'{"version": NaN, "name": null, "outbox": []}')

    def test_rule2_version(self):
        for v in [True, "1", 2, 1.5, None]:
            with self.subTest(v=v):
                self.bad({"version": v, "name": None, "outbox": []})
        self.bad({"name": None, "outbox": []})

    def test_rule3_name(self):
        self.bad({"version": 1, "outbox": []})
        self.bad({"version": 1, "name": "", "outbox": []})
        self.bad({"version": 1, "name": 5, "outbox": []})

    def test_rule4_outbox(self):
        self.bad({"version": 1, "name": "a"})
        self.bad({"version": 1, "name": "a", "outbox": {}})
        self.bad({"version": 1, "name": None, "outbox": [entry()]})

    def test_rule5_entries(self):
        bad_entries = [
            "x", entry(i="0B6C1F4E-2F0A-4C1E-9A53-0F7E1F3D2B11"), entry(i="nope"),
            entry(i=ID1 + "\n"), entry(to=""), entry(to=3), entry(text=""), entry(text=None),
            entry(text="x" * 8193), entry(text="é" * 4097), {"id": ID1, "to": "bob"},
        ]
        for e in bad_entries:
            with self.subTest(e=e):
                self.bad({"version": 1, "name": "a", "outbox": [e]})

    def test_rule6_unique_ids(self):
        self.bad({"version": 1, "name": "a", "outbox": [entry(), entry(text="other")]})


class SaveLoadTest(unittest.TestCase):
    def test_missing_file_and_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "a", "b")
            self.assertEqual(storage.load(d), (None, []))
            self.assertFalse(os.path.exists(d))
            storage.save(d, "alice", [dict(entry(text="héllo\n"), extra=1)])
            self.assertEqual(storage.load(d), ("alice", [entry(text="héllo\n")]))
            self.assertFalse(os.path.exists(os.path.join(d, "state.json.tmp")))
            with open(os.path.join(d, "state.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["version"], 1)

    def test_leftover_tmp_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "state.json.tmp"), "w") as f:
                f.write("garbage")
            self.assertEqual(storage.load(tmp), (None, []))

    def test_invalid_file_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.json")
            with open(path, "wb") as f:
                f.write(b"{}")
            with self.assertRaises(StateError):
                storage.load(tmp)
            with open(path, "rb") as f:
                self.assertEqual(f.read(), b"{}")


if __name__ == "__main__":
    unittest.main()
