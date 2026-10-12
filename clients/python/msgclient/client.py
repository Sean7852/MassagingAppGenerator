# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""Client state machine (20-client.md) and the program's main function."""
import asyncio
import os
import sys
import threading
import traceback
import uuid
from collections import deque

from websockets.asyncio.client import connect

from . import frames
from .cli import USAGE, UsageError, parse_args, parse_command
from .output import Formatter, write_line
from .storage import MAX_TEXT_BYTES, StateError, load_state, save_state, utf8_len

IDLE = "idle"
OFFLINE = "offline"
CONNECTING = "connecting"
ONLINE = "online"


def _start_stdin_thread(loop, queue):
    def put(event):
        try:
            loop.call_soon_threadsafe(queue.put_nowait, event)
            return True
        except RuntimeError:  # loop already closed
            return False

    def run():
        while True:
            try:
                line = sys.stdin.readline() if sys.stdin is not None else ""
            except Exception:
                traceback.print_exc(file=sys.stderr)
                line = ""
            if line == "":
                put(("eof",))
                return
            if line.endswith("\n"):
                line = line[:-1]
            if not put(("line", line)):
                return

    threading.Thread(target=run, name="stdin-reader", daemon=True).start()


class Client:
    def __init__(self, server, data_dir, machine, name, outbox):
        self.server = server
        self.data_dir = data_dir
        self.fmt = Formatter(machine)
        self.name = name
        self.outbox = outbox
        self.state = IDLE if name is None else OFFLINE
        self.in_flight = False
        self.seen = set()
        self.conn = None
        self.events = None
        self.pending = deque()  # stdin events held up while going online
        self.background = set()

    # ---- helpers -------------------------------------------------------

    def emit(self, line):
        write_line(line)

    def save(self):
        try:
            save_state(self.data_dir, self.name, self.outbox)
        except Exception as e:
            sys.stderr.write(f"cannot save state in {self.data_dir}: {e}\n")
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(1)

    def spawn(self, coro):
        task = asyncio.create_task(coro)
        self.background.add(task)
        task.add_done_callback(self.background.discard)
        return task

    async def _close(self, ws):
        try:
            await ws.close()
        except Exception:
            pass

    def drop_connection(self):
        """Close the current connection on purpose; anything from it is ignored afterwards."""
        ws = self.conn
        self.conn = None
        self.in_flight = False
        if ws is not None:
            self.spawn(self._close(ws))

    async def send_frame(self, frame):
        ws = self.conn
        if ws is None:
            return
        try:
            await ws.send(frames.encode(frame))
        except Exception:
            # The connection is closing; its "closed" event will follow.
            pass

    async def read_frames(self, ws):
        try:
            async for message in ws:
                if isinstance(message, str):
                    self.events.put_nowait(("frame", ws, message))
        except Exception:
            pass
        self.events.put_nowait(("closed", ws))

    async def send_next(self):
        if self.state == ONLINE and not self.in_flight and self.outbox:
            self.in_flight = True
            m = self.outbox[0]
            await self.send_frame({"type": "send", "id": m["id"], "to": m["to"], "text": m["text"]})

    # ---- main loop -----------------------------------------------------

    async def run(self):
        self.events = asyncio.Queue()
        _start_stdin_thread(asyncio.get_running_loop(), self.events)
        if self.state == OFFLINE:
            await self.guarded(self.go_online(self.name, from_login=False))
        while True:
            event = self.pending.popleft() if self.pending else await self.events.get()
            kind = event[0]
            if kind == "eof":
                await self.quit()
                return
            if kind == "line":
                if await self.guarded(self.handle_line(event[1])) is True:
                    return
            elif kind == "frame":
                if event[1] is self.conn and self.state == ONLINE:
                    await self.guarded(self.handle_frame(event[2]))
            elif kind == "closed":
                if event[1] is self.conn and self.state == ONLINE:
                    self.conn = None
                    self.in_flight = False
                    self.state = OFFLINE
                    self.emit(self.fmt.disconnected())

    async def guarded(self, coro):
        try:
            return await coro
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return None

    async def quit(self):
        self.emit(self.fmt.bye())
        ws = self.conn
        self.conn = None
        if ws is not None:
            await self._close(ws)

    # ---- commands ------------------------------------------------------

    async def handle_line(self, line):
        """Handle one command. Returns True when the client must exit."""
        cmd = parse_command(line)
        kind = cmd[0]
        if kind == "empty":
            return False
        if kind == "quit":
            await self.quit()
            return True
        if kind == "unknown":
            self.emit(self.fmt.error("unknown_command", "unknown command"))
        elif kind == "usage":
            self.emit(self.fmt.error("usage", cmd[1]))
        elif kind == "login":
            if self.state != IDLE:
                self.emit(self.fmt.error("already_logged_in", "already logged in"))
            else:
                await self.go_online(cmd[1], from_login=True)
        elif kind == "online":
            if self.state == IDLE:
                self.not_logged_in()
            elif self.state == ONLINE:
                self.emit(self.fmt.error("already_online", "already online"))
            else:
                await self.go_online(self.name, from_login=False)
        elif kind == "offline":
            if self.state == IDLE:
                self.not_logged_in()
            elif self.state == OFFLINE:
                self.emit(self.fmt.error("already_offline", "already offline"))
            else:
                self.drop_connection()
                self.state = OFFLINE
                self.emit(self.fmt.offline())
        elif kind == "send":
            await self.send_command(cmd[1], cmd[2])
        return False

    def not_logged_in(self):
        self.emit(self.fmt.error("not_logged_in", "log in first with /login <name>"))

    async def send_command(self, to, text):
        if self.state == IDLE:
            self.not_logged_in()
            return
        if utf8_len(text) > MAX_TEXT_BYTES:
            self.emit(self.fmt.error("too_long", "message too long (max 8192 bytes)"))
            return
        message = {"id": str(uuid.uuid4()), "to": to, "text": text}
        self.outbox.append(message)
        self.save()
        self.emit(self.fmt.queued(message["id"], to, text))
        await self.send_next()

    # ---- going online --------------------------------------------------

    async def go_online(self, login_name, from_login):
        fallback = IDLE if from_login else OFFLINE
        self.state = CONNECTING
        try:
            ws = await connect(
                self.server,
                open_timeout=5,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=1,
                max_size=64 * 1024,
                proxy=None,
            )
        except Exception:
            self.emit(self.fmt.error("connect_failed", f"cannot connect to {self.server}"))
            self.state = fallback
            return
        self.conn = ws
        self.in_flight = False
        self.spawn(self.read_frames(ws))
        await self.send_frame({"type": "login", "name": login_name})
        while True:
            event = await self.events.get()
            kind = event[0]
            if kind in ("line", "eof"):
                self.pending.append(event)
                continue
            if event[1] is not ws:
                continue  # from an old connection
            if kind == "closed":
                self.conn = None
                self.state = fallback
                self.emit(self.fmt.disconnected())
                return
            frame = frames.decode(event[2])
            if frame is None:
                continue
            if frame["type"] == "login_ok":
                name = frames.login_ok(frame)
                if name is None:
                    continue
                if from_login:
                    self.name = name
                    self.save()
                self.state = ONLINE
                self.emit(self.fmt.logged_in(name))
                await self.send_next()
                return
            if frame["type"] == "error":
                err = frames.error(frame)
                if err is None:
                    continue
                code, message, ref = err
                self.emit(self.fmt.error(code, message, ref))
                self.drop_connection()
                self.state = fallback
                return
            # any other frame while connecting is ignored

    # ---- frames while online -------------------------------------------

    def in_flight_id(self):
        return self.outbox[0]["id"] if self.in_flight and self.outbox else None

    async def handle_frame(self, raw):
        frame = frames.decode(raw)
        if frame is None:
            return
        t = frame["type"]
        if t == "ack":
            parsed = frames.ack(frame)
            if parsed is None:
                return
            id_, seq = parsed
            if id_ != self.in_flight_id():
                return
            message = self.outbox.pop(0)
            self.in_flight = False
            self.save()
            self.emit(self.fmt.sent(id_, seq, message["to"]))
            await self.send_next()
        elif t == "deliver":
            parsed = frames.deliver(frame)
            if parsed is None:
                return
            seq, id_, from_, text = parsed
            key = (from_, id_)
            if key not in self.seen:
                self.seen.add(key)
                self.emit(self.fmt.recv(seq, id_, from_, text))
            await self.send_frame({"type": "deliver_ack", "seq": seq})
        elif t == "error":
            parsed = frames.error(frame)
            if parsed is None:
                return
            code, message, ref = parsed
            if ref is not None and ref == self.in_flight_id():
                self.outbox.pop(0)
                self.in_flight = False
                self.save()
                self.emit(self.fmt.error(code, message, ref))
                await self.send_next()
            else:
                self.emit(self.fmt.error(code, message, ref))
        # login_ok while online and unknown types are ignored


def main(argv):
    try:
        server, data_dir, machine = parse_args(argv)
    except UsageError as e:
        sys.stderr.write(f"error: {e}\n{USAGE}\n")
        return 2
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    if sys.stdin is not None:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace", newline=None)
    try:
        name, outbox = load_state(data_dir)
    except StateError as e:
        sys.stderr.write(f"cannot load saved state from {data_dir}: {e}\n")
        return 1
    client = Client(server, data_dir, machine, name, outbox)
    asyncio.run(client.run())
    sys.stdout.flush()
    return 0
