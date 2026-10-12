# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""The client: state machine, commands, frames (spec/core/20-client.md, extension 10)."""

import asyncio
import collections
import os
import sys
import threading
import traceback
import uuid

from websockets.asyncio.client import connect

from . import frames, storage
from .commands import parse_line
from .output import Formatter, write_line

IDLE, OFFLINE, CONNECTING, ONLINE = "idle", "offline", "connecting", "online"
MAX_TEXT_BYTES = 8192


def report(message):
    sys.stderr.write(message + "\n")
    sys.stderr.flush()


class Client:
    def __init__(self, server, data_dir, machine, name, outbox):
        self.server = server
        self.data_dir = data_dir
        self.fmt = Formatter(machine)
        self.name = name
        self.outbox = outbox
        self.state = IDLE if name is None else OFFLINE
        self.conn = None
        self.in_flight = False
        self.seen = set()
        self.seen_receipts = set()
        self.queue = None
        self.pending = collections.deque()

    # ---- helpers -------------------------------------------------------------

    def save(self):
        try:
            storage.save(self.data_dir, self.name, self.outbox)
        except Exception as exc:
            report("cannot save state in %s: %s" % (self.data_dir, exc))
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(1)

    async def send_frame(self, ws, frame):
        try:
            await ws.send(frames.encode(frame))
        except Exception as exc:
            # The connection is going away; its "closed" event follows.
            report("send failed: %r" % (exc,))

    async def close_current(self):
        """Close the current connection on purpose; nothing more arrives from it."""
        ws, self.conn = self.conn, None
        self.in_flight = False
        if ws is not None:
            try:
                await ws.close()
            except Exception as exc:
                report("close failed: %r" % (exc,))

    async def reader(self, ws):
        try:
            async for message in ws:
                if isinstance(message, str):
                    self.queue.put_nowait(("frame", ws, message))
        except Exception:
            pass
        finally:
            self.queue.put_nowait(("closed", ws, None))

    def stdin_thread(self, loop):
        def hand_over(item):
            try:
                loop.call_soon_threadsafe(self.queue.put_nowait, item)
            except RuntimeError:
                pass  # loop already closed

        while True:
            try:
                line = sys.stdin.readline()
            except Exception as exc:
                report("stdin read failed: %r" % (exc,))
                line = ""
            if line == "":
                hand_over(("eof",))
                return
            if line.endswith("\n"):
                line = line[:-1]
            hand_over(("line", line))

    # ---- main loop -----------------------------------------------------------

    async def run(self):
        self.queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        threading.Thread(target=self.stdin_thread, args=(loop,), daemon=True).start()
        if self.state == OFFLINE:
            await self.guarded(self.go_online(self.name, login=False))
        while True:
            item = self.pending.popleft() if self.pending else await self.queue.get()
            quit_now = await self.guarded(self.handle(item))
            if quit_now:
                return

    async def guarded(self, coro):
        try:
            return await coro
        except Exception:
            report("internal error:\n" + traceback.format_exc())
            return False

    async def handle(self, item):
        kind = item[0]
        if kind == "eof":
            await self.quit()
            return True
        if kind == "line":
            command = parse_line(item[1])
            if command is None:
                return False
            return await self.command(command)
        _, ws, data = item
        if ws is not self.conn or self.state != ONLINE:
            return False
        if kind == "closed":
            self.conn = None
            self.in_flight = False
            self.state = OFFLINE
            write_line(self.fmt.disconnected())
            return False
        frame = frames.decode(data)
        if frame is not None:
            await self.on_frame(ws, frame)
        return False

    # ---- going online --------------------------------------------------------

    async def go_online(self, name, login):
        fail_state = IDLE if login else OFFLINE
        self.state = CONNECTING
        try:
            ws = await connect(self.server, open_timeout=5, ping_interval=20,
                               ping_timeout=20, close_timeout=1,
                               max_size=64 * 1024, proxy=None)
        except Exception as exc:
            report("connect failed: %r" % (exc,))
            self.state = fail_state
            write_line(self.fmt.error("connect_failed", "cannot connect to " + self.server))
            return False
        self.conn = ws
        self.in_flight = False
        asyncio.get_running_loop().create_task(self.reader(ws))
        await self.send_frame(ws, {"type": "login", "name": name})
        while True:
            item = await self.queue.get()
            if item[0] in ("line", "eof"):
                self.pending.append(item)
                continue
            kind, item_ws, data = item
            if item_ws is not ws or self.conn is not ws:
                continue
            if kind == "closed":
                self.conn = None
                self.state = fail_state
                write_line(self.fmt.disconnected())
                return False
            frame = frames.decode(data)
            if frame is None:
                continue
            if frame["type"] == "login_ok":
                if login:
                    self.name = frame["name"]
                    self.save()
                self.state = ONLINE
                write_line(self.fmt.logged_in(frame["name"]))
                await self.pump()
                return False
            if frame["type"] == "error":
                write_line(self.fmt.error(frame["code"], frame["message"], frame["ref"]))
                await self.close_current()
                self.state = fail_state
                return False
            # any other frame while connecting is ignored

    # ---- commands ------------------------------------------------------------

    async def command(self, command):
        name = command[0]
        fmt = self.fmt
        if name == "unknown":
            write_line(fmt.error("unknown_command", "unknown command"))
        elif name == "usage":
            write_line(fmt.error("usage", command[1]))
        elif name == "login":
            if self.state != IDLE:
                write_line(fmt.error("already_logged_in", "already logged in"))
            else:
                await self.go_online(command[1], login=True)
        elif name == "online":
            if self.state == IDLE:
                self.not_logged_in()
            elif self.state == ONLINE:
                write_line(fmt.error("already_online", "already online"))
            else:
                await self.go_online(self.name, login=False)
        elif name == "offline":
            if self.state == IDLE:
                self.not_logged_in()
            elif self.state == OFFLINE:
                write_line(fmt.error("already_offline", "already offline"))
            else:
                await self.close_current()
                self.state = OFFLINE
                write_line(fmt.offline())
        elif name == "send":
            await self.send_command(command[1], command[2])
        elif name == "quit":
            await self.quit()
            return True
        return False

    def not_logged_in(self):
        write_line(self.fmt.error("not_logged_in", "log in first with /login <name>"))

    async def send_command(self, to, text):
        if self.state == IDLE:
            self.not_logged_in()
            return
        if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
            write_line(self.fmt.error("too_long", "message too long (max 8192 bytes)"))
            return
        msg = {"id": str(uuid.uuid4()), "to": to, "text": text}
        self.outbox.append(msg)
        self.save()
        write_line(self.fmt.queued(msg["id"], to, text))
        await self.pump()

    async def quit(self):
        write_line(self.fmt.bye())
        await self.close_current()

    # ---- sending the outbox --------------------------------------------------

    async def pump(self):
        if self.state != ONLINE or self.in_flight or not self.outbox or self.conn is None:
            return
        msg = self.outbox[0]
        self.in_flight = True
        await self.send_frame(self.conn, {"type": "send", "id": msg["id"],
                                          "to": msg["to"], "text": msg["text"]})

    # ---- frames while online -------------------------------------------------

    async def on_frame(self, ws, frame):
        ftype = frame["type"]
        in_flight_id = self.outbox[0]["id"] if self.in_flight and self.outbox else None
        if ftype == "ack":
            if in_flight_id is not None and frame["id"] == in_flight_id:
                msg = self.outbox.pop(0)
                self.in_flight = False
                self.save()
                write_line(self.fmt.sent(msg["id"], frame["seq"], msg["to"]))
                await self.pump()
        elif ftype == "error":
            ref = frame["ref"]
            if in_flight_id is not None and ref == in_flight_id:
                self.outbox.pop(0)
                self.in_flight = False
                self.save()
                write_line(self.fmt.error(frame["code"], frame["message"], ref))
                await self.pump()
            else:
                write_line(self.fmt.error(frame["code"], frame["message"], ref))
        elif ftype == "deliver":
            key = (frame["from"], frame["id"])
            if key not in self.seen:
                self.seen.add(key)
                write_line(self.fmt.recv(frame["seq"], frame["id"], frame["from"],
                                         frame["text"]))
            await self.send_frame(ws, {"type": "deliver_ack", "seq": frame["seq"]})
        elif ftype == "receipt":
            key = (frame["by"], frame["msg_id"])
            if key not in self.seen_receipts:
                self.seen_receipts.add(key)
                write_line(self.fmt.read(frame["msg_id"], frame["msg_seq"], frame["by"]))
            await self.send_frame(ws, {"type": "deliver_ack", "seq": frame["seq"]})
        # login_ok while online and unknown types: ignored
