# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""Client state machine (spec/core/20-client.md, spec/extensions/10-read-receipts.md)."""

import asyncio
import collections
import os
import re
import sys
import threading
import traceback
import uuid

from websockets.asyncio.client import connect

from . import protocol, storage
from .cli import parse_command
from .output import format_line, write_line

NAME_RE = re.compile(r"[a-z0-9_]{1,32}")
MAX_TEXT_BYTES = 8192

IDLE, OFFLINE, CONNECTING, ONLINE = "idle", "offline", "connecting", "online"

EOF = object()  # stdin sentinel


def fatal(message):
    """Exit with status 1 (state could not be loaded or saved)."""
    try:
        sys.stdout.flush()
    except Exception:
        pass
    sys.stderr.write(message + "\n")
    sys.stderr.flush()
    os._exit(1)


class Client:
    def __init__(self, server, data_dir, machine):
        self.server = server
        self.data_dir = data_dir
        self.machine = machine
        self.state = IDLE
        self.name = None
        self.outbox = []
        self.in_flight = False
        self.seen = set()
        self.seen_receipts = set()
        self.ws = None
        self.events = None
        self.held = collections.deque()  # stdin lines held while going online
        self.done = False

    # ----- output -------------------------------------------------------------------------

    def emit(self, event, **fields):
        write_line(format_line(self.machine, event, **fields))

    def error(self, code, message, ref=None):
        self.emit("ERROR", code=code, message=message, ref=ref)

    def save(self):
        try:
            storage.save_outbox(self.data_dir, self.name, self.outbox)
        except Exception as e:
            fatal("cannot save state: %s" % e)

    # ----- connection helpers -------------------------------------------------------------

    async def _reader(self, ws):
        try:
            async for msg in ws:
                self.events.put_nowait(("frame", ws, msg))
        except Exception:
            pass
        self.events.put_nowait(("closed", ws, None))

    async def _send(self, frame):
        ws = self.ws
        if ws is None:
            return
        try:
            await ws.send(protocol.encode(frame))
        except Exception:
            pass  # the close event will follow

    def _drop_connection(self):
        """Close the current connection on purpose; anything still arriving is ignored."""
        ws = self.ws
        self.ws = None
        self.in_flight = False
        if ws is not None:
            asyncio.ensure_future(self._close_quietly(ws))

    @staticmethod
    async def _close_quietly(ws):
        try:
            await ws.close()
        except Exception:
            pass

    # ----- going online -------------------------------------------------------------------

    async def go_online(self):
        """Returns "online", "connect_failed", "error" or "closed"."""
        self.state = CONNECTING
        try:
            ws = await connect(self.server, open_timeout=5, ping_interval=20, ping_timeout=20,
                               close_timeout=1, max_size=64 * 1024, proxy=None)
        except Exception:
            self.error("connect_failed", "cannot connect to %s" % self.server)
            self.state = OFFLINE
            return "connect_failed"
        self.ws = ws
        asyncio.ensure_future(self._reader(ws))
        await self._send({"type": "login", "name": self.name})
        while True:
            kind, conn, payload = await self.events.get()
            if kind == "line":
                self.held.append(payload)
                continue
            if conn is not self.ws:
                continue
            if kind == "closed":
                self.ws = None
                self.state = OFFLINE
                self.emit("DISCONNECTED")
                return "closed"
            frame = protocol.parse_frame(payload)
            if frame is None:
                continue
            if frame["type"] == "login_ok":
                self.state = ONLINE
                self.in_flight = False
                self.emit("LOGGED_IN", name=frame["name"])
                await self.send_next()
                return "online"
            if frame["type"] == "error":
                self.error(frame["code"], frame["message"], frame["ref"])
                self._drop_connection()
                self.state = OFFLINE
                return "error"

    # ----- outbox -------------------------------------------------------------------------

    async def send_next(self):
        if self.state != ONLINE or self.in_flight or not self.outbox or self.ws is None:
            return
        m = self.outbox[0]
        self.in_flight = True
        await self._send({"type": "send", "id": m["id"], "to": m["to"], "text": m["text"]})

    # ----- commands -----------------------------------------------------------------------

    async def handle_line(self, line):
        if line is EOF:
            await self.quit()
            return
        cmd = parse_command(line)
        kind = cmd[0]
        if kind == "empty":
            return
        if kind == "unknown":
            self.error("unknown_command", "unknown command")
        elif kind == "usage":
            self.error("usage", cmd[1])
        elif kind == "quit":
            await self.quit()
        elif kind == "login":
            await self.cmd_login(cmd[1])
        elif kind == "online":
            if self.state == IDLE:
                self.error("not_logged_in", "log in first with /login <name>")
            elif self.state == ONLINE:
                self.error("already_online", "already online")
            else:
                await self.go_online()
        elif kind == "offline":
            if self.state == IDLE:
                self.error("not_logged_in", "log in first with /login <name>")
            elif self.state == OFFLINE:
                self.error("already_offline", "already offline")
            else:
                self._drop_connection()
                self.state = OFFLINE
                self.emit("OFFLINE")
        elif kind == "send":
            await self.cmd_send(cmd[1], cmd[2])

    async def cmd_login(self, name):
        if self.state != IDLE:
            self.error("already_logged_in", "already logged in")
            return
        if not NAME_RE.fullmatch(name):
            self.error("invalid_name", "name must match ^[a-z0-9_]{1,32}$")
            return
        try:
            self.outbox = storage.load_outbox(self.data_dir, name)
        except storage.StateError as e:
            fatal("cannot load state: %s" % e)
        self.name = name
        self.state = OFFLINE
        if await self.go_online() == "connect_failed":
            self.emit("OFFLINE")

    async def cmd_send(self, to, text):
        if self.state == IDLE:
            self.error("not_logged_in", "log in first with /login <name>")
            return
        if len(text.encode("utf-8", "surrogatepass")) > MAX_TEXT_BYTES:
            self.error("too_long", "message too long (max 8192 bytes)")
            return
        m = {"id": str(uuid.uuid4()), "to": to, "text": text}
        self.outbox.append(m)
        self.save()
        self.emit("QUEUED", id=m["id"], to=to, text=text)
        await self.send_next()

    async def quit(self):
        self.emit("BYE")
        self.done = True
        ws = self.ws
        self.ws = None
        if ws is not None:
            await self._close_quietly(ws)

    # ----- frames -------------------------------------------------------------------------

    async def handle_conn_event(self, kind, conn, payload):
        if conn is not self.ws or self.state != ONLINE:
            return
        if kind == "closed":
            self.ws = None
            self.in_flight = False
            self.emit("DISCONNECTED")
            self.state = OFFLINE
            return
        frame = protocol.parse_frame(payload)
        if frame is None:
            return
        t = frame["type"]
        if t == "ack":
            if self.in_flight and self.outbox and frame["id"] == self.outbox[0]["id"]:
                m = self.outbox.pop(0)
                self.in_flight = False
                self.save()
                self.emit("SENT", id=m["id"], seq=frame["seq"], to=m["to"])
                await self.send_next()
        elif t == "error":
            ref = frame["ref"]
            if ref is not None and self.in_flight and self.outbox and ref == self.outbox[0]["id"]:
                self.outbox.pop(0)
                self.in_flight = False
                self.save()
                self.error(frame["code"], frame["message"], ref)
                await self.send_next()
            else:
                self.error(frame["code"], frame["message"], ref)
        elif t == "deliver":
            key = (frame["from"], frame["id"])
            if key not in self.seen:
                self.seen.add(key)
                self.emit("RECV", seq=frame["seq"], id=frame["id"], from_=frame["from"],
                          text=frame["text"])
            await self._send({"type": "deliver_ack", "seq": frame["seq"]})
        elif t == "receipt":
            key = (frame["by"], frame["msg_id"])
            if key not in self.seen_receipts:
                self.seen_receipts.add(key)
                self.emit("READ", msg_id=frame["msg_id"], msg_seq=frame["msg_seq"],
                          by=frame["by"])
            await self._send({"type": "deliver_ack", "seq": frame["seq"]})
        # login_ok while online and unknown types: ignored

    # ----- main loop ----------------------------------------------------------------------

    def _start_stdin_thread(self, loop):
        def run():
            while True:
                try:
                    line = sys.stdin.readline()
                except Exception:
                    traceback.print_exc(file=sys.stderr)
                    line = ""
                if line == "":
                    loop.call_soon_threadsafe(self.events.put_nowait, ("line", None, EOF))
                    return
                if line.endswith("\n"):
                    line = line[:-1]
                loop.call_soon_threadsafe(self.events.put_nowait, ("line", None, line))

        threading.Thread(target=run, daemon=True).start()

    async def run(self):
        self.events = asyncio.Queue()
        self._start_stdin_thread(asyncio.get_running_loop())
        while not self.done:
            if self.held:
                kind, conn, payload = "line", None, self.held.popleft()
            else:
                kind, conn, payload = await self.events.get()
            try:
                if kind == "line":
                    await self.handle_line(payload)
                else:
                    await self.handle_conn_event(kind, conn, payload)
            except Exception:
                traceback.print_exc(file=sys.stderr)
