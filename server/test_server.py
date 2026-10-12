"""Protocol-level tests for server/server.py (rules in spec/core/10-protocol.md).

Hand-written. Starts the real server on a free port and talks raw WebSocket frames to it,
so server bugs show up before any client exists. Clients are tested separately by conformance/.

Run:
    python server/test_server.py
"""

from __future__ import annotations

import asyncio
import itertools
import json
import subprocess
import sys
import unittest
import uuid
from pathlib import Path
from typing import Any

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

SERVER = Path(__file__).with_name("server.py")
TIMEOUT = 3.0
QUIET = 0.3  # how long "nothing else arrives" is checked for

_names = itertools.count(1)


def unique(name: str) -> str:
    """Server state lives for the whole test run, so every test uses fresh user names."""
    return f"{name}_{next(_names)}"


def new_id() -> str:
    return str(uuid.uuid4())


class Client:
    def __init__(self, ws: ClientConnection):
        self.ws = ws

    async def send(self, frame: dict[str, Any] | str) -> None:
        await self.ws.send(frame if isinstance(frame, str) else json.dumps(frame))

    async def expect(self, type_: str, **fields: Any) -> dict[str, Any]:
        """The next frame must have this type and these field values."""
        frame = json.loads(await asyncio.wait_for(self.ws.recv(), TIMEOUT))
        assert frame["type"] == type_, f"expected {type_}, got {frame}"
        for key, value in fields.items():
            assert frame.get(key) == value, f"expected {key}={value!r} in {frame}"
        return frame

    async def expect_nothing(self) -> None:
        try:
            frame = await asyncio.wait_for(self.ws.recv(), QUIET)
        except TimeoutError:
            return
        raise AssertionError(f"expected no frame, got {frame}")

    async def send_msg(self, to: str, text: str, msg_id: str | None = None) -> dict[str, Any]:
        """Send a message and return its ack."""
        msg_id = msg_id or new_id()
        await self.send({"type": "send", "id": msg_id, "to": to, "text": text})
        return await self.expect("ack", id=msg_id)

    async def receive(self, **fields: Any) -> dict[str, Any]:
        """Expect a deliver frame and acknowledge it."""
        frame = await self.expect("deliver", **fields)
        await self.send({"type": "deliver_ack", "seq": frame["seq"]})
        return frame

    async def close(self) -> None:
        await self.ws.close()


class ServerTest(unittest.IsolatedAsyncioTestCase):
    proc: subprocess.Popen[str]
    url: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.proc = subprocess.Popen([sys.executable, str(SERVER), "--port", "0"],
                                    stdout=subprocess.PIPE, text=True)
        line = cls.proc.stdout.readline().strip()
        if not line.startswith("LISTENING port="):
            cls.proc.kill()
            raise RuntimeError(f"server did not start, got: {line!r}")
        cls.url = f"ws://127.0.0.1:{line.split('=')[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.proc.terminate()
        cls.proc.wait(TIMEOUT)

    async def asyncSetUp(self) -> None:
        self.clients: list[Client] = []

    async def asyncTearDown(self) -> None:
        for c in self.clients:
            await c.close()

    async def connect(self) -> Client:
        c = Client(await connect(self.url))
        self.clients.append(c)
        return c

    async def login(self, name: str) -> Client:
        c = await self.connect()
        await c.send({"type": "login", "name": name})
        await c.expect("login_ok", name=name)
        return c

    # ---- login ---------------------------------------------------------------------

    async def test_first_frame_must_be_login(self) -> None:
        c = await self.connect()
        await c.send({"type": "send", "id": new_id(), "to": "bob", "text": "hi"})
        await c.expect("error", code="not_logged_in")

    async def test_invalid_names_are_rejected(self) -> None:
        for name in ["Alice", "", "a" * 33, "al ice", "alice!"]:
            with self.subTest(name=name):
                c = await self.connect()
                await c.send({"type": "login", "name": name})
                await c.expect("error", code="invalid_name")

    async def test_valid_name_edge_cases(self) -> None:
        for name in ["a", "a" * 32, "user_42"]:
            with self.subTest(name=name):
                await self.login(name)

    async def test_login_twice_on_one_connection(self) -> None:
        c = await self.login(unique("alice"))
        await c.send({"type": "login", "name": unique("bob")})
        await c.expect("error", code="already_logged_in")

    async def test_newest_session_wins(self) -> None:
        name = unique("alice")
        old = await self.login(name)
        new = await self.login(name)
        await old.expect("error", code="session_replaced")
        with self.assertRaises(ConnectionClosed) as closed:
            await asyncio.wait_for(old.ws.recv(), TIMEOUT)
        self.assertEqual(closed.exception.rcvd.code, 4001)
        # The new session works and receives messages.
        bob = await self.login(unique("bob"))
        await bob.send_msg(name, "still there?")
        await new.receive(text="still there?")

    # ---- bad frames ----------------------------------------------------------------

    async def test_bad_frames_keep_connection_open(self) -> None:
        c = await self.login(unique("alice"))
        for raw, code in [("hello", "bad_request"), ("[1, 2]", "bad_request"),
                          ('{"no_type": 1}', "bad_request"),
                          ('{"type": "dance"}', "unknown_type")]:
            with self.subTest(raw=raw):
                await c.send(raw)
                await c.expect("error", code=code)
        await c.send_msg(unique("bob"), "connection still works")

    async def test_invalid_send_errors_carry_ref(self) -> None:
        c = await self.login(unique("alice"))
        bad = [
            {"to": "Bob", "text": "hi"},          # invalid recipient name
            {"to": "bob", "text": ""},            # empty text
            {"to": "bob", "text": "x" * 4097},    # text too long
        ]
        for fields in bad:
            with self.subTest(fields=fields):
                msg_id = new_id()
                await c.send({"type": "send", "id": msg_id, **fields})
                await c.expect("error", ref=msg_id)

    async def test_send_without_valid_id(self) -> None:
        c = await self.login(unique("alice"))
        for msg_id in ["not-a-uuid", new_id().upper(), 42]:
            with self.subTest(id=msg_id):
                await c.send({"type": "send", "id": msg_id, "to": "bob", "text": "hi"})
                await c.expect("error", code="bad_request")

    # ---- delivery ------------------------------------------------------------------

    async def test_online_delivery(self) -> None:
        a_name, b_name = unique("alice"), unique("bob")
        a, b = await self.login(a_name), await self.login(b_name)
        msg_id = new_id()
        ack = await a.send_msg(b_name, "hello", msg_id)
        await b.receive(seq=ack["seq"], id=msg_id, text="hello", **{"from": a_name, "to": b_name})

    async def test_seq_strictly_increases(self) -> None:
        a = await self.login(unique("alice"))
        to = unique("bob")
        seqs = [(await a.send_msg(to, f"m{i}"))["seq"] for i in range(5)]
        self.assertEqual(seqs, sorted(set(seqs)))

    async def test_message_to_never_seen_user_is_held(self) -> None:
        a = await self.login(unique("alice"))
        newcomer = unique("newcomer")
        await a.send_msg(newcomer, "welcome")
        n = await self.login(newcomer)
        await n.receive(text="welcome")

    async def test_mailbox_delivered_in_seq_order(self) -> None:
        a = await self.login(unique("alice"))
        b_name = unique("bob")
        seqs = [(await a.send_msg(b_name, f"m{i}"))["seq"] for i in range(5)]
        b = await self.login(b_name)
        for i, seq in enumerate(seqs):
            await b.receive(seq=seq, text=f"m{i}")
        await b.expect_nothing()

    async def test_redelivered_until_deliver_ack(self) -> None:
        a = await self.login(unique("alice"))
        b_name = unique("bob")
        seq = (await a.send_msg(b_name, "important"))["seq"]

        b = await self.login(b_name)
        await b.expect("deliver", seq=seq)    # received but NOT acked
        await b.close()

        b = await self.login(b_name)
        await b.receive(seq=seq)              # pushed again, acked this time
        await b.close()

        b = await self.login(b_name)
        await b.expect_nothing()              # gone after the ack

    async def test_deliver_ack_is_idempotent(self) -> None:
        b = await self.login(unique("bob"))
        await b.send({"type": "deliver_ack", "seq": 999_999})
        await b.send({"type": "deliver_ack", "seq": 999_999})
        await b.expect_nothing()

    async def test_resend_same_id_is_deduplicated(self) -> None:
        a_name, b_name = unique("alice"), unique("bob")
        a, b = await self.login(a_name), await self.login(b_name)
        msg_id = new_id()
        first = await a.send_msg(b_name, "once", msg_id)
        await b.receive(text="once")
        again = await a.send_msg(b_name, "once", msg_id)
        self.assertEqual(again["seq"], first["seq"])
        await b.expect_nothing()

    async def test_same_id_from_different_senders_is_not_a_duplicate(self) -> None:
        b_name = unique("bob")
        a, c = await self.login(unique("alice")), await self.login(unique("carol"))
        msg_id = new_id()
        s1 = (await a.send_msg(b_name, "from alice", msg_id))["seq"]
        s2 = (await c.send_msg(b_name, "from carol", msg_id))["seq"]
        self.assertNotEqual(s1, s2)

    async def test_send_to_self(self) -> None:
        name = unique("alice")
        a = await self.login(name)
        msg_id = new_id()
        await a.send({"type": "send", "id": msg_id, "to": name, "text": "note"})
        # ack and deliver both arrive; the ack comes first.
        await a.expect("ack", id=msg_id)
        await a.receive(id=msg_id, text="note")

    # ---- the assignment scenario ---------------------------------------------------

    async def test_alice_bob_offline_scenario(self) -> None:
        alice, bob = unique("alice"), unique("bob")
        a, b = await self.login(alice), await self.login(bob)

        # Alice -> Bob, Bob -> Alice, both online.
        await a.send_msg(bob, "Hi Bob, I have something important to tell you")
        await b.receive(text="Hi Bob, I have something important to tell you")
        await b.send_msg(alice, "What is it?")
        await a.receive(text="What is it?")

        # Both go offline and queue a message locally (nothing reaches the server).
        await a.close()
        await b.close()

        # Alice reconnects; her queued message reaches the server.
        a = await self.login(alice)
        await a.send_msg(bob, "Alice's queued message")
        # Alice goes offline again.
        await a.close()

        # Bob reconnects: receives Alice's message and delivers his own queued one.
        b = await self.login(bob)
        await b.receive(text="Alice's queued message")
        await b.send_msg(alice, "Bob's queued message")
        await b.expect_nothing()

        # Alice gets Bob's message when she next connects.
        a = await self.login(alice)
        await a.receive(text="Bob's queued message")
        await a.expect_nothing()


if __name__ == "__main__":
    unittest.main(verbosity=2)
