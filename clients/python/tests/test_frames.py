# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
import unittest

from msgclient import frames


class FramesTest(unittest.TestCase):
    def test_decode(self):
        self.assertIsNone(frames.decode("nope"))
        self.assertIsNone(frames.decode("[1]"))
        self.assertIsNone(frames.decode('{"type":5}'))
        self.assertEqual(frames.decode('{"type":"x","y":1}'), {"type": "x", "y": 1})

    def test_seq(self):
        self.assertEqual(frames.seq_value(7), 7)
        self.assertEqual(frames.seq_value(7.0), 7)
        for bad in ["7", 0, -1, 7.5, True, None, 2**53, float("nan"), float("inf")]:
            self.assertIsNone(frames.seq_value(bad), repr(bad))

    def test_error_ref(self):
        self.assertEqual(frames.error({"code": "c", "message": "m"}), ("c", "m", None))
        self.assertEqual(frames.error({"code": "c", "message": "m", "ref": None}), ("c", "m", None))
        self.assertEqual(frames.error({"code": "c", "message": "m", "ref": "r"}), ("c", "m", "r"))
        self.assertIsNone(frames.error({"code": "c", "message": "m", "ref": 1}))
        self.assertIsNone(frames.error({"code": "c"}))

    def test_deliver_and_ack(self):
        d = {"seq": 1, "id": "i", "from": "a", "text": "t"}
        self.assertEqual(frames.deliver(d), (1, "i", "a", "t"))
        self.assertIsNone(frames.deliver({**d, "text": 1}))
        self.assertIsNone(frames.deliver({**d, "seq": "1"}))
        self.assertEqual(frames.ack({"id": "i", "seq": 2.0}), ("i", 2))
        self.assertIsNone(frames.ack({"id": "i"}))

    def test_encode_compact(self):
        self.assertEqual(frames.encode({"type": "login", "name": "é"}), '{"type":"login","name":"é"}')


if __name__ == "__main__":
    unittest.main()
