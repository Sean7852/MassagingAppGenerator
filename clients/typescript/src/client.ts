// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { randomUUID } from "node:crypto";
import WebSocket from "ws";
import { parseCommand } from "./commands.js";
import { parseFrame, type ServerFrame } from "./frames.js";
import { formatEvent, writeLine, type Event } from "./output.js";
import { loadOutbox, saveOutbox, MAX_TEXT_BYTES, type OutboxEntry } from "./storage.js";
import type { Options } from "./args.js";

const NAME_RE = /^[a-z0-9_]{1,32}$/;
const CONNECT_TIMEOUT_MS = 5000;
const PING_INTERVAL_MS = 20000;
const PONG_TIMEOUT_MS = 20000;

type State = "idle" | "offline" | "connecting" | "online";

/** One WebSocket connection and its timers. */
interface Conn {
  ws: WebSocket;
  opened: boolean;
  connectTimer?: NodeJS.Timeout;
  pingTimer?: NodeJS.Timeout;
  pongTimer?: NodeJS.Timeout;
}

type QueueItem =
  | { k: "line"; line: string }
  | { k: "eof" }
  | { k: "open"; c: Conn }
  | { k: "message"; c: Conn; data: string }
  | { k: "close"; c: Conn }
  | { k: "connect_timeout"; c: Conn };

export class Client {
  private state: State = "idle";
  private name = "";
  private outbox: OutboxEntry[] = [];
  private inFlight = false;
  private conn: Conn | null = null;
  private loginInProgress = false;
  private readonly seen = new Set<string>();
  private readonly seenReceipts = new Set<string>();

  private readonly queue: QueueItem[] = [];
  private wake: (() => void) | null = null;
  private done = false;

  constructor(private readonly opts: Options) {}

  // ---- event queue -------------------------------------------------------

  push(item: QueueItem): void {
    this.queue.push(item);
    const w = this.wake;
    this.wake = null;
    w?.();
  }

  pushLine(line: string): void {
    this.push({ k: "line", line });
  }

  pushEof(): void {
    this.push({ k: "eof" });
  }

  /** Takes the next item; while going online, stdin items stay queued. */
  private take(): QueueItem | undefined {
    const connOnly = this.state === "connecting";
    const idx = this.queue.findIndex((it) => !connOnly || (it.k !== "line" && it.k !== "eof"));
    if (idx < 0) return undefined;
    return this.queue.splice(idx, 1)[0];
  }

  async run(): Promise<void> {
    while (!this.done) {
      const item = this.take();
      if (item === undefined) {
        await new Promise<void>((resolve) => (this.wake = resolve));
        continue;
      }
      try {
        this.handle(item);
      } catch (err) {
        console.error("internal error:", err);
      }
    }
  }

  private handle(item: QueueItem): void {
    switch (item.k) {
      case "line":
        return this.handleLine(item.line);
      case "eof":
        return this.quit();
      default:
        if (item.c !== this.conn) return; // old connection: ignored
        return this.handleConnEvent(item);
    }
  }

  // ---- output ------------------------------------------------------------

  private emit(e: Event): void {
    writeLine(formatEvent(e, this.opts.machine));
  }

  private error(code: string, message: string): void {
    this.emit({ kind: "ERROR", code, message });
  }

  private fatal(message: string): void {
    this.done = true;
    this.dropConn();
    process.stdin.destroy();
    console.error(message);
    process.stdout.write("", () => process.exit(1));
  }

  private save(): boolean {
    try {
      saveOutbox(this.opts.dataDir, this.name, this.outbox);
      return true;
    } catch (err) {
      this.fatal(`cannot save the outbox: ${(err as Error).message}`);
      return false;
    }
  }

  // ---- commands ----------------------------------------------------------

  private handleLine(line: string): void {
    const cmd = parseCommand(line);
    switch (cmd.kind) {
      case "empty":
        return;
      case "unknown":
        return this.error("unknown_command", "unknown command");
      case "usage": {
        const usage: Record<string, string> = {
          login: "usage: /login <name>",
          send: "usage: /send <user> <text>",
          online: "usage: /online",
          offline: "usage: /offline",
          quit: "usage: /quit",
        };
        return this.error("usage", usage[cmd.command]);
      }
      case "quit":
        return this.quit();
      case "login":
        return this.login(cmd.name);
      case "online":
        if (this.state === "idle") return this.error("not_logged_in", "log in first with /login <name>");
        if (this.state === "online") return this.error("already_online", "already online");
        return this.goOnline();
      case "offline":
        if (this.state === "idle") return this.error("not_logged_in", "log in first with /login <name>");
        if (this.state === "offline") return this.error("already_offline", "already offline");
        this.dropConn();
        this.state = "offline";
        this.inFlight = false;
        return this.emit({ kind: "OFFLINE" });
      case "send":
        return this.send(cmd.to, cmd.text);
    }
  }

  private login(name: string): void {
    if (this.state !== "idle") return this.error("already_logged_in", "already logged in");
    if (!NAME_RE.test(name)) return this.error("invalid_name", "name must match ^[a-z0-9_]{1,32}$");
    let outbox: OutboxEntry[];
    try {
      outbox = loadOutbox(this.opts.dataDir, name);
    } catch (err) {
      return this.fatal(`cannot load the outbox: ${(err as Error).message}`);
    }
    this.outbox = outbox;
    this.name = name;
    this.state = "offline";
    this.loginInProgress = true;
    this.goOnline();
  }

  private send(to: string, text: string): void {
    if (this.state === "idle") return this.error("not_logged_in", "log in first with /login <name>");
    if (Buffer.byteLength(text, "utf8") > MAX_TEXT_BYTES) {
      return this.error("too_long", "message too long (max 8192 bytes)");
    }
    const msg: OutboxEntry = { id: randomUUID(), to, text };
    this.outbox.push(msg);
    if (!this.save()) return;
    this.emit({ kind: "QUEUED", id: msg.id, to, text });
    this.pump();
  }

  private quit(): void {
    this.emit({ kind: "BYE" });
    this.done = true;
    this.dropConn();
    process.stdin.destroy();
    process.exitCode = 0;
  }

  // ---- connection --------------------------------------------------------

  private goOnline(): void {
    this.state = "connecting";
    let ws: WebSocket;
    try {
      ws = new WebSocket(this.opts.server, { maxPayload: 64 * 1024, handshakeTimeout: CONNECT_TIMEOUT_MS });
    } catch {
      this.connectFailed();
      return;
    }
    const c: Conn = { ws, opened: false };
    this.conn = c;
    c.connectTimer = setTimeout(() => this.push({ k: "connect_timeout", c }), CONNECT_TIMEOUT_MS);
    ws.on("error", () => {
      /* a close event always follows */
    });
    ws.on("open", () => {
      c.opened = true;
      clearTimeout(c.connectTimer);
      this.startKeepAlive(c);
      this.push({ k: "open", c });
    });
    ws.on("message", (data: WebSocket.RawData, isBinary: boolean) => {
      if (isBinary) return;
      const buf = Array.isArray(data)
        ? Buffer.concat(data)
        : Buffer.isBuffer(data)
          ? data
          : Buffer.from(data);
      this.push({ k: "message", c, data: buf.toString("utf8") });
    });
    ws.on("pong", () => {
      clearTimeout(c.pongTimer);
      c.pongTimer = undefined;
    });
    ws.on("close", () => {
      this.clearTimers(c);
      this.push({ k: "close", c });
    });
  }

  private startKeepAlive(c: Conn): void {
    c.pingTimer = setInterval(() => {
      try {
        c.ws.ping();
      } catch {
        return;
      }
      if (c.pongTimer === undefined) {
        c.pongTimer = setTimeout(() => c.ws.terminate(), PONG_TIMEOUT_MS);
      }
    }, PING_INTERVAL_MS);
  }

  private clearTimers(c: Conn): void {
    clearTimeout(c.connectTimer);
    clearInterval(c.pingTimer);
    clearTimeout(c.pongTimer);
    c.pongTimer = undefined;
  }

  /** Closes the current connection on purpose; anything later from it is ignored. */
  private dropConn(): void {
    const c = this.conn;
    if (c === null) return;
    this.conn = null;
    this.clearTimers(c);
    if (!c.opened) {
      c.ws.terminate();
      return;
    }
    c.ws.close();
    // Do not let a dead peer hold the process for the close handshake.
    setTimeout(() => c.ws.terminate(), 2000).unref();
  }

  private connectFailed(): void {
    this.dropConn();
    this.state = "offline";
    this.error("connect_failed", `cannot connect to ${this.opts.server}`);
    if (this.loginInProgress) this.emit({ kind: "OFFLINE" });
    this.loginInProgress = false;
  }

  private sendFrame(frame: object): void {
    try {
      this.conn?.ws.send(JSON.stringify(frame));
    } catch (err) {
      console.error("send failed:", err);
    }
  }

  private handleConnEvent(item: Exclude<QueueItem, { k: "line" } | { k: "eof" }>): void {
    const c = item.c;
    switch (item.k) {
      case "connect_timeout":
        if (!c.opened && this.state === "connecting") this.connectFailed();
        return;
      case "open":
        this.sendFrame({ type: "login", name: this.name });
        return;
      case "close":
        this.conn = null;
        if (this.state === "connecting" && !c.opened) return this.connectFailed();
        this.state = "offline";
        this.inFlight = false;
        this.loginInProgress = false;
        return this.emit({ kind: "DISCONNECTED" });
      case "message": {
        const f = parseFrame(item.data);
        if (f === null) return;
        if (this.state === "connecting") return this.handleLoginAnswer(f);
        if (this.state === "online") return this.handleFrame(f);
        return;
      }
    }
  }

  private handleLoginAnswer(f: ServerFrame): void {
    if (f.type === "login_ok") {
      this.state = "online";
      this.loginInProgress = false;
      this.emit({ kind: "LOGGED_IN", name: f.name });
      this.pump();
    } else if (f.type === "error") {
      this.emit({ kind: "ERROR", code: f.code, ref: f.ref, message: f.message });
      this.dropConn();
      this.state = "offline";
      this.loginInProgress = false;
    }
  }

  private handleFrame(f: ServerFrame): void {
    const head = this.outbox[0];
    switch (f.type) {
      case "ack":
        if (!this.inFlight || head === undefined || f.id !== head.id) return;
        this.outbox.shift();
        this.inFlight = false;
        if (!this.save()) return;
        this.emit({ kind: "SENT", id: head.id, seq: f.seq, to: head.to });
        return this.pump();
      case "error":
        if (this.inFlight && head !== undefined && f.ref === head.id) {
          this.outbox.shift();
          this.inFlight = false;
          if (!this.save()) return;
          this.emit({ kind: "ERROR", code: f.code, ref: f.ref, message: f.message });
          return this.pump();
        }
        return this.emit({ kind: "ERROR", code: f.code, ref: f.ref, message: f.message });
      case "deliver": {
        const key = JSON.stringify([f.from, f.id]);
        if (!this.seen.has(key)) {
          this.seen.add(key);
          this.emit({ kind: "RECV", seq: f.seq, id: f.id, from: f.from, text: f.text });
        }
        return this.sendFrame({ type: "deliver_ack", seq: f.seq });
      }
      case "receipt": {
        const key = JSON.stringify([f.by, f.msg_id]);
        if (!this.seenReceipts.has(key)) {
          this.seenReceipts.add(key);
          this.emit({ kind: "READ", id: f.msg_id, seq: f.msg_seq, by: f.by });
        }
        return this.sendFrame({ type: "deliver_ack", seq: f.seq });
      }
      case "login_ok":
        return;
    }
  }

  /** Sends the first outbox message if online and nothing is in flight. */
  private pump(): void {
    if (this.state !== "online" || this.inFlight || this.outbox.length === 0) return;
    const m = this.outbox[0];
    this.inFlight = true;
    this.sendFrame({ type: "send", id: m.id, to: m.to, text: m.text });
  }
}
