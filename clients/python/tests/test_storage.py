# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
import json
import tempfile
import unittest

from msgclient import storage
from msgclient.protocol import parse_frame, seq_value
from msgclient.storage import StateError, validate_state

ID = "0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11"
ID2 = "9e1d7c2a-4b3f-4a8e-b1c6-7d5e3f2a1b09"


def enc(obj):
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def entry(**kw):
    e = {"id": ID, "to": "bob", "text": "hi"}
    e.update(kw)
    return e


class ValidateTest(unittest.TestCase):
    def ok(self, data):
        return validate_state(data)

    def bad(self, data):
        with self.assertRaises(StateError):
            validate_state(data)

    def test_valid(self):
        self.assertEqual(self.ok(enc({"version": 2, "outbox": []})), [])
        self.assertEqual(self.ok(enc({"version": 2.0, "outbox": [entry(x=1)], "extra": 1})),
                         [entry()])
        self.ok(enc({"version": 2, "outbox": [entry(text="é" * 4096)]}))

    def test_rule1_json_object(self):
        self.bad(b"\xef\xbb\xbf" + enc({"version": 2, "outbox": []}))
        self.bad(b"not json")
        self.bad(b"[]")
        self.bad(b'{"version": 2, "outbox": [], "x": "\xff"}')
        self.bad(b'{"version": 2, "outbox": [], "x": NaN}')

    def test_rule2_version(self):
        self.bad(enc({"outbox": []}))
        self.bad(enc({"version": True, "outbox": []}))
        self.bad(enc({"version": "2", "outbox": []}))
        self.bad(enc({"version": 1, "outbox": []}))

    def test_rule3_outbox(self):
        self.bad(enc({"version": 2}))
        self.bad(enc({"version": 2, "outbox": {}}))

    def test_rule4_entries(self):
        for e in ["x", entry(id="ABC"), entry(id=ID.upper()), entry(id=None), entry(to=""),
                  entry(to=1), entry(text=""), entry(text=5), entry(text="x" * 8193),
                  entry(text="é" * 4097)]:
            self.bad(enc({"version": 2, "outbox": [e]}))
        no_id = entry()
        del no_id["id"]
        self.bad(enc({"version": 2, "outbox": [no_id]}))

    def test_rule5_unique(self):
        self.bad(enc({"version": 2, "outbox": [entry(), entry(text="other")]}))
        self.ok(enc({"version": 2, "outbox": [entry(), entry(id=ID2)]}))

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(storage.load_outbox(d, "alice"), [])
            box = [entry(text="héllo\n👋")]
            storage.save_outbox(d, "alice", box)
            self.assertEqual(storage.load_outbox(d, "alice"), box)


class FrameTest(unittest.TestCase):
    def test_seq(self):
        self.assertEqual(seq_value(7), 7)
        self.assertEqual(seq_value(7.0), 7)
        for v in ("7", 0, -1, 7.5, True, None, 2 ** 53):
            self.assertIsNone(seq_value(v))

    def test_frames(self):
        self.assertIsNone(parse_frame(b"{}"))
        self.assertIsNone(parse_frame("nope"))
        self.assertIsNone(parse_frame("[1]"))
        self.assertIsNone(parse_frame('{"type":"what"}'))
        self.assertIsNone(parse_frame('{"type":"ack","id":"x","seq":"1"}'))
        self.assertEqual(parse_frame('{"type":"ack","id":"x","seq":1.0}'),
                         {"type": "ack", "id": "x", "seq": 1})
        self.assertIsNone(parse_frame('{"type":"error","code":"c","message":"m","ref":1}'))
        self.assertEqual(parse_frame('{"type":"error","code":"c","message":"m","ref":null}')["ref"],
                         None)
        self.assertIsNotNone(parse_frame('{"type":"deliver","seq":1,"id":"i","from":"a","text":"t"}'))
        self.assertIsNone(parse_frame('{"type":"deliver","seq":1,"id":"i","text":"t"}'))
        self.assertIsNone(parse_frame('{"type":"receipt","seq":1,"msg_seq":0,"msg_id":"i","by":"b"}'))
        self.assertIsNotNone(parse_frame('{"type":"receipt","seq":1,"msg_seq":2,"msg_id":"i","by":"b"}'))


if __name__ == "__main__":
    unittest.main()
