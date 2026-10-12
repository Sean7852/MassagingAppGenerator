# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
import unittest

from msgclient.args import ArgError, parse_args


class ArgParsingTest(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(parse_args([]), {
            "server": "ws://127.0.0.1:8765", "data_dir": ".msgdata", "machine": False})

    def test_all_options(self):
        self.assertEqual(
            parse_args(["--machine", "--server", "ws://h:1", "--data-dir=d"]),
            {"server": "ws://h:1", "data_dir": "d", "machine": True})
        self.assertEqual(
            parse_args(["--data-dir", "x y", "--server=ws://a=b"]),
            {"server": "ws://a=b", "data_dir": "x y", "machine": False})

    def test_errors(self):
        bad = [
            ["--unknown"], ["-h"], ["--help"], ["--serv", "ws://x"], ["--machine", "--machine"],
            ["--server", "a", "--server", "b"], ["--server=a", "--server=b"],
            ["--server"], ["--data-dir"], ["--server="], ["--data-dir", ""],
            ["--server", ""], ["positional"], ["--machine=1"],
        ]
        for argv in bad:
            with self.subTest(argv=argv):
                with self.assertRaises(ArgError):
                    parse_args(argv)


if __name__ == "__main__":
    unittest.main()
