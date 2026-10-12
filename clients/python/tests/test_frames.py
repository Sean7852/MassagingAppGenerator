# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
import unittest

from msgclient.frames import decode, encode


class FrameDecodeTest(unittest.TestCase):
    def test_seq_rules(self):
        self.assertEqual(decode('{"type":"ack","id":"x","seq":7.0}')["seq"], 7)
        for seq in ['"7"', "0", "-1", "7.5", "true", "9007199254740992", "null"]:
            with self.subTest(seq=seq):
                self.assertIsNone(decode('{"type":"ack","id":"x","seq":%s}' % seq))

    def test_error_ref(self):
        self.assertIsNone(decode('{"type":"error","code":"c","message":"m"}')["ref"])
        self.assertIsNone(decode('{"type":"error","code":"c","message":"m","ref":null}')["ref"])
        self.assertIsNone(decode('{"type":"error","code":"c","message":"m","ref":1}'))

    def test_broken_and_unknown(self):
        self.assertIsNone(decode("nope"))
        self.assertIsNone(decode("[1]"))
        self.assertIsNone(decode('{"type":1}'))
        self.assertIsNone(decode('{"type":"deliver","seq":1,"id":"i","from":"a"}'))
        self.assertEqual(decode('{"type":"whatever","x":1}'), {"type": "whatever"})
        d = decode('{"type":"deliver","seq":1,"id":"i","from":"a","to":5,"text":"t","z":0}')
        self.assertEqual(d["text"], "t")
        self.assertIsNone(decode('{"type":"receipt","seq":4,"msg_seq":"3","msg_id":"i","by":"b"}'))

    def test_encode_compact(self):
        self.assertEqual(encode({"type": "login", "name": "é"}), '{"type":"login","name":"é"}')


if __name__ == "__main__":
    unittest.main()
