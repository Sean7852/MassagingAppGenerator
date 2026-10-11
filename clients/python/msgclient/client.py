# GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.
"""Client state machine (spec/core/20-client.md).

Every event (stdin line, end of input, connection opened/failed, frame, close) goes through one
asyncio.Queue and is handled to completion before the next one.
"""
import asyncio
import json
import sys
import threading
import traceback
import uuid

from websockets.asyncio.client import connect

from . import output
from .commands import parse

IDLE = "idle"
CONNECTING = "connecting"
ONLINE = "online"


def _log(text):
    print(text, file=sys.stderr, flush=True)


async def default_connector(url):
    return await connect(url, open_timeout=5, max_size=64 * 1024)


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _encode(frame):
    return json.dumps(frame, separators=(",", ":"), ensure_ascii=False)


class Client:
    def __init__(self, url, out=output.write_line, connector=default_connector):
        self.url = url
        self.out = out
        self.connector = connector
        self.state = IDLE
        self.name = None
        self.conn = None
        self.connect_task = None
        self.reader_task = None
        self.send_queue = []  # list of dicts: id, to, text
        self.in_flight = False
        self.seen = set()  # (from, id)
        self.events = asyncio.Queue()

    # ----- event plumbing -------------------------------------------------

    def post(self, event):
        self.events.put_nowait(event)

    async def run(self, read_stdin=True):
        if read_stdin:
            loop = asyncio.get_running_loop()
            t = threading.Thread(target=_stdin_reader, args=(loop, self.post), daemon=True)
            t.start()
        while True:
            event = await self.events.get()
            try:
                if await self.handle(event):
                    return
            except Exception:
                traceback.print_exc(file=sys.stderr)

    async def handle(self, event):
        """Handle one event. Returns True when the client must exit."""
        kind = event[0]
        if kind == "line":
            return await self.on_line(event[1])
        if kind == "eof":
            return await self.quit()
        if kind == "opened":
            await self.on_opened(event[1], event[2])
        elif kind == "connect_failed":
            self.on_connect_failed()
        elif kind == "frame":
            await self.on_frame(event[1], event[2])
        elif kind == "closed":
            self.on_closed(event[1])
        return False

    # ----- commands -------------------------------------------------------

    async def on_line(self, line):
        cmd = parse(line)
        kind = cmd[0]
        if kind == "empty":
            pass
        elif kind == "login":
            if self.state != IDLE:
                self.out(output.error("already_logged_in", output.MSG_ALREADY_LOGGED_IN))
            else:
                self.state = CONNECTING
                self.connect_task = asyncio.create_task(self._open(cmd[1]))
        elif kind == "send":
            if self.state != ONLINE:
                self.out(output.error("not_logged_in", output.MSG_NOT_LOGGED_IN))
            else:
                self.send_queue.append({"id": str(uuid.uuid4()), "to": cmd[1], "text": cmd[2]})
                await self._pump()
        elif kind == "quit":
            return await self.quit()
        elif kind == "usage":
            self.out(output.error("usage", output.USAGE_MESSAGES[cmd[1]]))
        else:
            self.out(output.error("unknown_command", output.MSG_UNKNOWN_COMMAND))
        return False

    async def quit(self):
        self.out(output.BYE)
        task = self.connect_task
        self.connect_task = None
        if task is not None:
            if task.done():
                if not task.cancelled() and task.exception() is None and task.result() is not None:
                    await _close(task.result())
            else:
                task.cancel()
        conn = self.conn
        self.conn = None
        if conn is not None:
            await _close(conn)
        self.send_queue.clear()
        self.in_flight = False
        self.state = IDLE
        return True

    # ----- connection -----------------------------------------------------

    async def _open(self, name):
        try:
            ws = await self.connector(self.url)
        except Exception as e:
            _log(f"connect failed: {e!r}")
            self.post(("connect_failed",))
            return None
        self.post(("opened", ws, name))
        return ws

    async def on_opened(self, ws, name):
        self.connect_task = None
        self.conn = ws
        await self._send({"type": "login", "name": name})
        self.reader_task = asyncio.create_task(self._read(ws))

    def on_connect_failed(self):
        self.connect_task = None
        self.state = IDLE
        self.out(output.error("connect_failed", output.msg_connect_failed(self.url)))

    async def _read(self, ws):
        try:
            async for data in ws:
                self.post(("frame", ws, data))
        except Exception as e:
            _log(f"connection error: {e!r}")
        self.post(("closed", ws))

    async def _send(self, frame):
        ws = self.conn
        if ws is None:
            return
        try:
            await ws.send(_encode(frame))
        except Exception as e:
            # The reader task reports the close; nothing else to do here.
            _log(f"send failed: {e!r}")

    async def _pump(self):
        if self.state == ONLINE and not self.in_flight and self.send_queue:
            self.in_flight = True
            m = self.send_queue[0]
            await self._send({"type": "send", "id": m["id"], "to": m["to"], "text": m["text"]})

    def on_closed(self, ws):
        if ws is not self.conn:
            return  # a connection we already closed or replaced
        self.conn = None
        self.reader_task = None
        if self.state == ONLINE:
            for m in self.send_queue:
                self.out(output.error("not_sent", output.MSG_NOT_SENT, m["id"]))
        self.send_queue.clear()
        self.in_flight = False
        self.out(output.DISCONNECTED)
        self.state = IDLE
        self.name = None

    # ----- frames ---------------------------------------------------------

    async def on_frame(self, ws, data):
        if ws is not self.conn or not isinstance(data, str):
            return
        try:
            frame = json.loads(data)
        except ValueError:
            return
        if not isinstance(frame, dict) or not isinstance(frame.get("type"), str):
            return
        ftype = frame["type"]
        if self.state == CONNECTING:
            if ftype == "login_ok":
                name = frame.get("name")
                if not isinstance(name, str):
                    return
                self.state = ONLINE
                self.name = name
                self.out(output.logged_in(name))
                await self._pump()
            elif ftype == "error":
                err = _error_fields(frame)
                if err is None:
                    return
                self.out(output.error(*err))
                self.conn = None
                self.reader_task = None
                self.state = IDLE
                await _close(ws)
        elif self.state == ONLINE:
            if ftype == "ack":
                await self._on_ack(frame)
            elif ftype == "error":
                await self._on_error(frame)
            elif ftype == "deliver":
                await self._on_deliver(frame)

    def _in_flight_id(self):
        if self.in_flight and self.send_queue:
            return self.send_queue[0]["id"]
        return None

    async def _on_ack(self, frame):
        msg_id, seq = frame.get("id"), frame.get("seq")
        if not isinstance(msg_id, str) or not _is_int(seq):
            return
        if msg_id != self._in_flight_id():
            return
        m = self.send_queue.pop(0)
        self.in_flight = False
        self.out(output.sent(m["id"], seq, m["to"]))
        await self._pump()

    async def _on_error(self, frame):
        err = _error_fields(frame)
        if err is None:
            return
        code, message, ref = err
        self.out(output.error(code, message, ref))
        if ref is not None and ref == self._in_flight_id():
            self.send_queue.pop(0)
            self.in_flight = False
            await self._pump()

    async def _on_deliver(self, frame):
        seq, msg_id = frame.get("seq"), frame.get("id")
        sender, text = frame.get("from"), frame.get("text")
        if not (_is_int(seq) and isinstance(msg_id, str)
                and isinstance(sender, str) and isinstance(text, str)):
            return
        key = (sender, msg_id)
        if key not in self.seen:
            self.seen.add(key)
            self.out(output.recv(seq, msg_id, sender, text))
        await self._send({"type": "deliver_ack", "seq": seq})


def _error_fields(frame):
    """(code, message, ref-or-None) of a well-formed error frame, else None."""
    code, message, ref = frame.get("code"), frame.get("message"), frame.get("ref")
    if not isinstance(code, str) or not isinstance(message, str):
        return None
    if not isinstance(ref, str):
        ref = None
    return code, message, ref


async def _close(ws):
    try:
        await ws.close()
    except Exception as e:
        _log(f"close failed: {e!r}")


def _stdin_reader(loop, post):
    """Background daemon thread: hands each stdin line (or end of input) to the event loop."""
    while True:
        try:
            line = sys.stdin.readline()
        except UnicodeDecodeError as e:
            _log(f"stdin decode error: {e!r}")
            continue
        except Exception as e:
            _log(f"stdin error: {e!r}")
            line = ""
        if line == "":
            event = ("eof",)
        else:
            event = ("line", line[:-1] if line.endswith("\n") else line)
        try:
            loop.call_soon_threadsafe(post, event)
        except RuntimeError:
            return  # loop is closed; the client has exited
        if line == "":
            return
