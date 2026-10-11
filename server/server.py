"""Messaging server: single process, in-memory, store-and-forward over WebSocket.

Hand-written (not under the generator). It implements the wire protocol described in
server/PROTOCOL.md, which is a draft until spec/core/10-protocol.md takes it over.

Run:
    python server/server.py --port 8765

Prints `LISTENING port=<n>` on stdout once it accepts connections, so test runners can
start it with `--port 0` (pick a free port) and read the real port from that line.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from typing import Any

from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed

log = logging.getLogger("server")

NAME_RE = re.compile(r"^[a-z0-9_]{1,32}$")
ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
MAX_TEXT_LEN = 4096
MAX_FRAME_BYTES = 64 * 1024

# Close codes (4000-4999 is the application range).
CLOSE_SESSION_REPLACED = 4001


class ProtocolError(Exception):
    def __init__(self, code: str, message: str, ref: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.ref = ref


@dataclass
class Message:
    seq: int
    id: str
    sender: str
    to: str
    text: str

    def deliver_frame(self) -> dict[str, Any]:
        return {"type": "deliver", "seq": self.seq, "id": self.id,
                "from": self.sender, "to": self.to, "text": self.text}


@dataclass
class Session:
    """One logged-in connection. All outbound frames go through `outbox` so their order
    on the wire is exactly the order they were enqueued in."""
    name: str
    ws: ServerConnection
    outbox: asyncio.Queue[dict[str, Any] | None] = field(default_factory=asyncio.Queue)

    def push(self, frame: dict[str, Any]) -> None:
        self.outbox.put_nowait(frame)


class Server:
    def __init__(self) -> None:
        self.next_seq = 1
        # (sender, id) -> seq, so a resent message is acked again instead of stored twice.
        self.accepted: dict[tuple[str, str], int] = {}
        # recipient -> undelivered messages in seq order; removed on deliver_ack.
        self.mailboxes: dict[str, list[Message]] = {}
        self.sessions: dict[str, Session] = {}

    # ---- connection lifecycle -------------------------------------------------------

    async def handle(self, ws: ServerConnection) -> None:
        session: Session | None = None
        writer: asyncio.Task[None] | None = None
        try:
            async for raw in ws:
                try:
                    frame = parse_frame(raw)
                    if session is None:
                        session = self.login(ws, frame)
                        writer = asyncio.create_task(write_loop(session))
                    else:
                        self.dispatch(session, frame)
                except ProtocolError as e:
                    err = {"type": "error", "code": e.code, "message": e.message}
                    if e.ref is not None:
                        err["ref"] = e.ref
                    if session is not None:
                        session.push(err)
                    else:
                        await ws.send(json.dumps(err))
        except ConnectionClosed:
            pass
        finally:
            if session is not None:
                if self.sessions.get(session.name) is session:
                    del self.sessions[session.name]
                    log.info("logout name=%s", session.name)
                session.outbox.put_nowait(None)
            if writer is not None:
                await writer

    def login(self, ws: ServerConnection, frame: dict[str, Any]) -> Session:
        if frame["type"] != "login":
            raise ProtocolError("not_logged_in", "first frame must be login")
        name = require_str(frame, "name")
        if not NAME_RE.match(name):
            raise ProtocolError("invalid_name", "name must match ^[a-z0-9_]{1,32}$")

        old = self.sessions.get(name)
        if old is not None:
            # Newest session wins: a client that lost its network without a clean close
            # must be able to log in again immediately.
            log.info("replace name=%s", name)
            old.push({"type": "error", "code": "session_replaced",
                      "message": "logged in from another connection"})
            old.outbox.put_nowait(None)
            asyncio.create_task(old.ws.close(CLOSE_SESSION_REPLACED, "session replaced"))

        session = Session(name, ws)
        self.sessions[name] = session
        log.info("login name=%s pending=%d", name, len(self.mailboxes.get(name, [])))
        session.push({"type": "login_ok", "name": name})
        for msg in self.mailboxes.get(name, []):
            session.push(msg.deliver_frame())
        return session

    # ---- frames from a logged-in client ---------------------------------------------

    def dispatch(self, session: Session, frame: dict[str, Any]) -> None:
        match frame["type"]:
            case "send":
                self.on_send(session, frame)
            case "deliver_ack":
                self.on_deliver_ack(session, frame)
            case "login":
                raise ProtocolError("already_logged_in", "this connection is already logged in")
            case other:
                raise ProtocolError("unknown_type", f"unknown frame type: {other}")

    def on_send(self, session: Session, frame: dict[str, Any]) -> None:
        msg_id = require_str(frame, "id")
        if not ID_RE.match(msg_id):
            raise ProtocolError("bad_request", "id must be a lowercase UUID")
        to = require_str(frame, "to")
        if not NAME_RE.match(to):
            raise ProtocolError("invalid_name", "to must match ^[a-z0-9_]{1,32}$", ref=msg_id)
        text = require_str(frame, "text")
        if not text or len(text) > MAX_TEXT_LEN:
            raise ProtocolError("bad_request", f"text must be 1..{MAX_TEXT_LEN} characters",
                                ref=msg_id)

        key = (session.name, msg_id)
        seq = self.accepted.get(key)
        if seq is not None:
            log.info("dup from=%s id=%s seq=%d", session.name, msg_id, seq)
            session.push({"type": "ack", "id": msg_id, "seq": seq})
            return

        msg = Message(self.next_seq, msg_id, session.name, to, text)
        self.next_seq += 1
        self.accepted[key] = msg.seq
        self.mailboxes.setdefault(to, []).append(msg)
        log.info("accept from=%s to=%s id=%s seq=%d", session.name, to, msg_id, msg.seq)

        session.push({"type": "ack", "id": msg_id, "seq": msg.seq})
        recipient = self.sessions.get(to)
        if recipient is not None:
            recipient.push(msg.deliver_frame())

    def on_deliver_ack(self, session: Session, frame: dict[str, Any]) -> None:
        seq = frame.get("seq")
        if not isinstance(seq, int) or isinstance(seq, bool):
            raise ProtocolError("bad_request", "seq must be an integer")
        box = self.mailboxes.get(session.name, [])
        # Unknown or already-acked seq is ignored, so deliver_ack is idempotent.
        remaining = [m for m in box if m.seq != seq]
        if len(remaining) != len(box):
            log.info("delivered to=%s seq=%d", session.name, seq)
        if remaining:
            self.mailboxes[session.name] = remaining
        else:
            self.mailboxes.pop(session.name, None)


async def write_loop(session: Session) -> None:
    while (frame := await session.outbox.get()) is not None:
        try:
            await session.ws.send(json.dumps(frame))
        except ConnectionClosed:
            return


def parse_frame(raw: str | bytes) -> dict[str, Any]:
    if isinstance(raw, bytes):
        raise ProtocolError("bad_request", "frames must be text, not binary")
    try:
        frame = json.loads(raw)
    except json.JSONDecodeError:
        raise ProtocolError("bad_request", "frame is not valid JSON") from None
    if not isinstance(frame, dict) or not isinstance(frame.get("type"), str):
        raise ProtocolError("bad_request", "frame must be a JSON object with a string 'type'")
    return frame


def require_str(frame: dict[str, Any], key: str) -> str:
    value = frame.get(key)
    if not isinstance(value, str):
        raise ProtocolError("bad_request", f"'{key}' must be a string")
    return value


async def main() -> None:
    parser = argparse.ArgumentParser(description="In-memory messaging server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765, help="0 picks a free port")
    parser.add_argument("--verbose", action="store_true", help="log protocol events to stderr")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(asctime)s %(name)s %(message)s", stream=sys.stderr)

    server = Server()
    async with serve(server.handle, args.host, args.port, max_size=MAX_FRAME_BYTES) as ws_server:
        port = ws_server.sockets[0].getsockname()[1]
        print(f"LISTENING port={port}", flush=True)
        await ws_server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
