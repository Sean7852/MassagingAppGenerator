// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { randomUUID } from "node:crypto";
import WebSocket from "ws";
import { parseCommand } from "./commands.js";
import { parseServerFrame, type ServerFrame } from "./frames.js";
import { formatEvent, type Event } from "./output.js";
import { saveState, type OutboxEntry } from "./storage.js";

const CONNECT_TIMEOUT_MS = 5000;
const PING_INTERVAL_MS = 20000;
const PONG_TIMEOUT_MS = 20000;
const CLOSE_GRACE_MS = 1000;
const MAX_TEXT_BYTES = 8192;

/** One WebSocket connection and its timers. */
class Conn {
  ws: WebSocket | null = null;
  opened = false;
  connectTimer: NodeJS.Timeout | undefined;
  pingTimer: NodeJS.Timeout | undefined;
  pongTimer: NodeJS.Timeout | undefined;

  clearTimers(): void {
    clearTimeout(this.connectTimer);
    clearInterval(this.pingTimer);
    clearTimeout(this.pongTimer);
    this.connectTimer = this.pingTimer = this.pongTimer = undefined;
  }
}

type QueuedEvent =
  | { kind: "line"; line: string }
  | { kind: "eof" }
  | { kind: "conn"; conn: Conn; what: "open" | "fail" | "close" }
  | { kind: "conn"; conn: Conn; what: "message"; data: string };

type ConnEvent = Extract<QueuedEvent, { kind: "conn" }>;

/** A single FIFO of stdin lines and connection events, consumed by one loop. */
class EventQueue {
  private items: QueuedEvent[] = [];
  private wake: (() => void) | null = null;

  push(ev: QueuedEvent): void {
    this.items.push(ev);
    const w = this.wake;
    this.wake = null;
    w?.();
  }

  /** Removes and returns the first event matching `pred`, waiting if there is none. */
  async take(pred: (ev: QueuedEvent) => boolean): Promise<QueuedEvent> {
    for (;;) {
      const i = this.items.findIndex(pred);
      if (i >= 0) return this.items.splice(i, 1)[0];
      await new Promise<void>((resolve) => (this.wake = resolve));
    }
  }
}

/** Raised when saving fails; the client then exits with status 1. */
class SaveFailed extends Error {}

type ConnState = "idle" | "offline" | "connecting" | "online";

export interface ClientOptions {
  server: string;
  dataDir: string;
  machine: boolean;
  name: string | null;
  outbox: OutboxEntry[];
  /** Called once when the client is done (after BYE, or when saving failed). */
  onStop: () => void;
}

export class Client {
  readonly queue = new EventQueue();
  private state: ConnState;
  private name: string | null;
  private outbox: OutboxEntry[];
  private inFlight = false;
  private conn: Conn | null = null;
  private readonly seen = new Set<string>();
  private readonly seenReceipts = new Set<string>();
  private done = false;

  constructor(private readonly opts: ClientOptions) {
    this.name = opts.name;
    this.outbox = [...opts.outbox];
    this.state = this.name === null ? "idle" : "offline";
  }

  pushLine(line: string): void {
    this.queue.push({ kind: "line", line });
  }

  pushEof(): void {
    this.queue.push({ kind: "eof" });
  }

  /** Runs the client until /quit, end of input, or a failed save. */
  async run(): Promise<void> {
    if (this.name !== null) {
      await this.guard(() => this.goOnline(this.name as string, false));
    }
    while (!this.done) {
      const ev = await this.queue.take(() => true);
      await this.guard(() => this.handle(ev));
    }
  }

  private async guard(fn: () => Promise<void> | void): Promise<void> {
    try {
      await fn();
    } catch (e) {
      if (e instanceof SaveFailed) {
        console.error(`cannot save state: ${e.message}`);
        this.done = true;
        this.shutdown();
        process.stdout.write("", () => process.exit(1));
        return;
      }
      console.error("internal error:", e);
    }
  }

  // ---- output and saving ---------------------------------------------------

  private print(ev: Event): void {
    process.stdout.write(formatEvent(ev, this.opts.machine) + "\n");
  }

  private error(code: string, message: string): void {
    this.print({ kind: "ERROR", code, message });
  }

  private save(): void {
    try {
      saveState(this.opts.dataDir, { name: this.name, outbox: this.outbox });
    } catch (e) {
      throw new SaveFailed((e as Error).message);
    }
  }

  // ---- event dispatch ------------------------------------------------------

  private async handle(ev: QueuedEvent): Promise<void> {
    if (ev.kind === "line") return this.handleLine(ev.line);
    if (ev.kind === "eof") return this.quit();
    if (ev.conn !== this.conn) return; // old connection, or none: ignore
    if (this.state !== "online") return;
    if (ev.what === "message") {
      const frame = parseServerFrame(ev.data);
      if (frame) this.handleOnlineFrame(frame);
    } else if (ev.what === "close") {
      this.dropConn();
      this.inFlight = false;
      this.state = "offline";
      this.print({ kind: "DISCONNECTED" });
    }
  }

  private async handleLine(line: string): Promise<void> {
    const cmd = parseCommand(line);
    switch (cmd.kind) {
      case "empty":
        return;
      case "unknown":
        return this.error("unknown_command", "unknown command");
      case "usage":
        return this.error("usage", cmd.message);
      case "quit":
        return this.quit();
      case "login":
        if (this.state !== "idle") return this.error("already_logged_in", "already logged in");
        return this.goOnline(cmd.name, true);
      case "online":
        if (this.state === "idle") return this.notLoggedIn();
        if (this.state === "online") return this.error("already_online", "already online");
        return this.goOnline(this.name as string, false);
      case "offline":
        if (this.state === "idle") return this.notLoggedIn();
        if (this.state === "offline") return this.error("already_offline", "already offline");
        this.closeConn();
        this.inFlight = false;
        this.state = "offline";
        this.print({ kind: "OFFLINE" });
        return;
      case "send": {
        if (this.state === "idle") return this.notLoggedIn();
        if (Buffer.byteLength(cmd.text, "utf8") > MAX_TEXT_BYTES) {
          return this.error("too_long", "message too long (max 8192 bytes)");
        }
        const msg: OutboxEntry = { id: randomUUID(), to: cmd.to, text: cmd.text };
        this.outbox.push(msg);
        this.save();
        this.print({ kind: "QUEUED", id: msg.id, to: msg.to, text: msg.text });
        this.sendNext();
        return;
      }
    }
  }

  private notLoggedIn(): void {
    this.error("not_logged_in", "log in first with /login <name>");
  }

  private quit(): void {
    this.print({ kind: "BYE" });
    this.closeConn();
    this.done = true;
    this.shutdown();
    process.exitCode = 0;
  }

  private shutdown(): void {
    this.conn?.clearTimers();
    this.opts.onStop();
  }

  // ---- going online --------------------------------------------------------

  /** Goes online with `name`; handles only connection events until the outcome is known. */
  private async goOnline(name: string, isLogin: boolean): Promise<void> {
    const failState: ConnState = isLogin ? "idle" : "offline";
    this.state = "connecting";
    const conn = this.openConn();
    for (;;) {
      const ev = (await this.queue.take((e) => e.kind === "conn")) as ConnEvent;
      if (ev.conn !== conn) continue; // an old connection
      if (ev.what === "open") {
        conn.ws?.send(JSON.stringify({ type: "login", name }));
      } else if (ev.what === "fail" || (ev.what === "close" && !conn.opened)) {
        this.dropConn(true);
        this.state = failState;
        this.error("connect_failed", `cannot connect to ${this.opts.server}`);
        return;
      } else if (ev.what === "close") {
        this.dropConn();
        this.state = failState;
        this.print({ kind: "DISCONNECTED" });
        return;
      } else if (ev.what === "message") {
        const frame = parseServerFrame(ev.data);
        if (frame === null) continue;
        if (frame.type === "login_ok") {
          if (isLogin) {
            this.name = frame.name;
            this.save();
          }
          this.state = "online";
          this.inFlight = false;
          this.print({ kind: "LOGGED_IN", name: frame.name });
          this.sendNext();
          return;
        }
        if (frame.type === "error") {
          this.printServerError(frame);
          this.closeConn();
          this.state = failState;
          return;
        }
        // any other frame while connecting is ignored
      }
    }
  }

  private openConn(): Conn {
    const conn = new Conn();
    this.conn = conn;
    const push = (what: "open" | "fail" | "close") => this.queue.push({ kind: "conn", conn, what });
    let ws: WebSocket;
    try {
      ws = new WebSocket(this.opts.server, { maxPayload: 64 * 1024, handshakeTimeout: CONNECT_TIMEOUT_MS });
    } catch {
      push("fail");
      return conn;
    }
    conn.ws = ws;
    conn.connectTimer = setTimeout(() => {
      if (!conn.opened) push("fail");
    }, CONNECT_TIMEOUT_MS);
    ws.on("open", () => {
      conn.opened = true;
      clearTimeout(conn.connectTimer);
      conn.pingTimer = setInterval(() => {
        try {
          ws.ping();
        } catch {
          // a closing socket will report its close event
        }
        if (conn.pongTimer === undefined) {
          conn.pongTimer = setTimeout(() => ws.terminate(), PONG_TIMEOUT_MS);
        }
      }, PING_INTERVAL_MS);
      push("open");
    });
    ws.on("pong", () => {
      clearTimeout(conn.pongTimer);
      conn.pongTimer = undefined;
    });
    ws.on("message", (data, isBinary) => {
      if (isBinary) return;
      const text = Buffer.isBuffer(data)
        ? data.toString("utf8")
        : Array.isArray(data)
          ? Buffer.concat(data).toString("utf8")
          : Buffer.from(data).toString("utf8");
      this.queue.push({ kind: "conn", conn, what: "message", data: text });
    });
    ws.on("error", () => {
      if (!conn.opened) push("fail");
      // after open, the close event that follows is what counts
    });
    ws.on("close", () => {
      conn.clearTimers();
      push("close");
    });
    return conn;
  }

  /** Forgets the current connection (it closed, or failed to open). */
  private dropConn(terminate = false): void {
    const conn = this.conn;
    this.conn = null;
    if (!conn) return;
    conn.clearTimers();
    if (terminate) {
      try {
        conn.ws?.terminate();
      } catch {
        // already gone
      }
    }
  }

  /** Closes the current connection on purpose; nothing from it counts any more. */
  private closeConn(): void {
    const conn = this.conn;
    this.conn = null;
    if (!conn) return;
    conn.clearTimers();
    const ws = conn.ws;
    if (!ws) return;
    try {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
        setTimeout(() => ws.terminate(), CLOSE_GRACE_MS).unref();
      } else {
        ws.terminate();
      }
    } catch {
      // already gone
    }
  }

  // ---- online ----------------------------------------------------------------

  private sendNext(): void {
    if (this.state !== "online" || this.inFlight || this.outbox.length === 0) return;
    const ws = this.conn?.ws;
    if (!ws) return;
    const m = this.outbox[0];
    ws.send(JSON.stringify({ type: "send", id: m.id, to: m.to, text: m.text }));
    this.inFlight = true;
  }

  private sendDeliverAck(seq: number): void {
    this.conn?.ws?.send(JSON.stringify({ type: "deliver_ack", seq }));
  }

  private printServerError(f: Extract<ServerFrame, { type: "error" }>): void {
    this.print({ kind: "ERROR", code: f.code, ref: f.ref, message: f.message });
  }

  private handleOnlineFrame(f: ServerFrame): void {
    switch (f.type) {
      case "login_ok":
        return;
      case "ack": {
        if (!this.inFlight || this.outbox[0]?.id !== f.id) return;
        const m = this.outbox.shift() as OutboxEntry;
        this.inFlight = false;
        this.save();
        this.print({ kind: "SENT", id: m.id, seq: f.seq, to: m.to });
        this.sendNext();
        return;
      }
      case "error": {
        if (f.ref !== undefined && this.inFlight && this.outbox[0]?.id === f.ref) {
          this.outbox.shift();
          this.inFlight = false;
          this.save();
          this.printServerError(f);
          this.sendNext();
          return;
        }
        this.printServerError(f);
        return;
      }
      case "deliver": {
        const key = JSON.stringify([f.from, f.id]);
        if (!this.seen.has(key)) {
          this.seen.add(key);
          this.print({ kind: "RECV", seq: f.seq, id: f.id, from: f.from, text: f.text });
        }
        this.sendDeliverAck(f.seq);
        return;
      }
      case "receipt": {
        const key = JSON.stringify([f.by, f.msgId]);
        if (!this.seenReceipts.has(key)) {
          this.seenReceipts.add(key);
          this.print({ kind: "READ", msgId: f.msgId, msgSeq: f.msgSeq, by: f.by });
        }
        this.sendDeliverAck(f.seq);
        return;
      }
    }
  }
}
