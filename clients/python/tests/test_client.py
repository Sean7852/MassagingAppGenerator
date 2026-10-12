# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""State machine tests with a fake connection (no server, no network)."""
import asyncio
import json
import unittest

from msgclient.client import Client


class FakeWs:
    def __init__(self):
        self.sent = []
        self.closed = False
        self.incoming = asyncio.Queue()

    async def send(self, data):
        self.sent.append(json.loads(data))

    async def close(self):
        self.closed = True

    def __aiter__(self):
        return self

    async def __anext__(self):
        item = await self.incoming.get()
        if item is None:
            raise StopAsyncIteration
        return item


class ClientTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.lines = []
        self.ws = FakeWs()
        self.fail_connect = False

        async def connector(url):
            if self.fail_connect:
                raise OSError("refused")
            return self.ws

        self.client = Client("ws://test:1", out=self.lines.append, connector=connector)

    async def drain(self):
        """Handle queued events until nothing more happens."""
        for _ in range(20):
            await asyncio.sleep(0)
            while not self.client.events.empty():
                await self.client.handle(self.client.events.get_nowait())

    async def line(self, text):
        result = await self.client.handle(("line", text))
        await self.drain()
        return result

    async def frame(self, obj):
        await self.client.handle(("frame", self.ws, json.dumps(obj)))
        await self.drain()

    async def login(self, name="alice"):
        await self.line(f"/login {name}")
        self.assertEqual(self.ws.sent[-1], {"type": "login", "name": name})
        await self.frame({"type": "login_ok", "name": name})

    async def test_login_and_send(self):
        await self.login()
        self.assertEqual(self.lines, ["LOGGED_IN name=alice"])
        await self.line("/send bob one")
        await self.line("/send bob two")
        sends = [f for f in self.ws.sent if f["type"] == "send"]
        self.assertEqual(len(sends), 1)
        first = sends[0]
        self.assertEqual((first["to"], first["text"]), ("bob", "one"))
        await self.frame({"type": "ack", "id": "other", "seq": 9})
        self.assertEqual(self.lines, ["LOGGED_IN name=alice"])
        await self.frame({"type": "ack", "id": first["id"], "seq": 1})
        self.assertEqual(self.lines[-1], f"SENT id={first['id']} seq=1 to=bob")
        second = self.ws.sent[-1]
        self.assertEqual((second["type"], second["text"]), ("send", "two"))
        await self.frame({"type": "error", "code": "invalid_name", "message": "m", "ref": second["id"]})
        self.assertEqual(self.lines[-1], f"ERROR code=invalid_name ref={second['id']} message=m")
        self.assertEqual(self.client.send_queue, [])

    async def test_receive_dedup_and_ack(self):
        await self.login()
        d = {"type": "deliver", "seq": 4, "id": "m1", "from": "bob", "to": "alice", "text": "a\nb"}
        await self.frame(d)
        await self.frame(dict(d, seq=5))
        self.assertEqual(self.lines[1:], ["RECV seq=4 id=m1 from=bob text=a\\nb"])
        acks = [f for f in self.ws.sent if f["type"] == "deliver_ack"]
        self.assertEqual(acks, [{"type": "deliver_ack", "seq": 4}, {"type": "deliver_ack", "seq": 5}])

    async def test_login_error_returns_to_idle(self):
        await self.line("/login Alice")
        await self.frame({"type": "error", "code": "invalid_name", "message": "bad"})
        self.assertEqual(self.lines, ["ERROR code=invalid_name message=bad"])
        self.assertTrue(self.ws.closed)
        self.assertEqual(self.client.state, "idle")
        await self.client.handle(("closed", self.ws))
        self.assertEqual(self.lines, ["ERROR code=invalid_name message=bad"])

    async def test_disconnect_reports_not_sent(self):
        await self.login()
        await self.line("/send bob one")
        await self.line("/send bob two")
        ids = [f["id"] for f in self.ws.sent if f["type"] == "send"]
        self.ws.incoming.put_nowait(None)  # connection ends
        await self.drain()
        self.assertEqual(self.client.state, "idle")
        queued_lines = self.lines[1:]
        self.assertEqual(len(queued_lines), 3)
        self.assertEqual(queued_lines[0],
                         f"ERROR code=not_sent ref={ids[0]} message=connection lost before the server acknowledged the message")
        self.assertTrue(queued_lines[1].startswith("ERROR code=not_sent ref="))
        self.assertEqual(queued_lines[2], "DISCONNECTED")

    async def test_close_while_connecting(self):
        await self.line("/login alice")
        self.ws.incoming.put_nowait(None)
        await self.drain()
        self.assertEqual(self.lines, ["DISCONNECTED"])
        self.assertEqual(self.client.state, "idle")

    async def test_connect_failed(self):
        self.fail_connect = True
        await self.line("/login alice")
        self.assertEqual(self.lines, ["ERROR code=connect_failed message=cannot connect to ws://test:1"])
        self.assertEqual(self.client.state, "idle")

    async def test_local_errors(self):
        await self.line("/send bob hi")
        await self.line("/login alice")
        await self.line("/login alice")
        self.assertEqual(self.lines, [
            "ERROR code=not_logged_in message=log in first with /login <name>",
            "ERROR code=already_logged_in message=already logged in or connecting",
        ])

    async def test_ignored_frames(self):
        await self.login()
        for raw in ("not json", "[1]", '{"type":"weird"}', '{"type":"login_ok","name":"x"}'):
            await self.client.handle(("frame", self.ws, raw))
        self.assertEqual(self.lines, ["LOGGED_IN name=alice"])

    async def test_quit(self):
        await self.login()
        await self.line("/send bob queued")
        self.assertTrue(await self.line("/quit"))
        self.assertEqual(self.lines[-1], "BYE")
        self.assertTrue(self.ws.closed)


if __name__ == "__main__":
    unittest.main()
