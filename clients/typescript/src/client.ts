// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { randomUUID } from "node:crypto";
import WebSocket from "ws";
import { parseCommand } from "./commands.js";
import { parseServerFrame, type ServerFrame } from "./frames.js";
import { formatLine, type OutEvent } from "./output.js";
import { MAX_TEXT_BYTES, saveState, type OutboxEntry, type SavedState } from "./storage.js";

type State = "idle" | "offline" | "connecting" | "online";

type QueueEvent =
  | { kind: "line"; line: string }
  | { kind: "eof" }
  | { kind: "open"; ws: WebSocket }
  | { kind: "message"; ws: WebSocket; data: string }
  | { kind: "close"; ws: WebSocket }
  | { kind: "ws_error"; ws: WebSocket }
  | { kind: "connect_timeout"; ws: WebSocket };

export interface ClientOptions {
  server: string;
  dataDir: string;
  machine: boolean;
  saved: SavedState;
  write: (line: string) => void;
  /** Called once after BYE was printed. */
  onQuit: () => void;
  /** Called when saving failed; the client has stopped. */
  onFatal: (message: string) => void;
}

const CONNECT_TIMEOUT_MS = 5000;
const PING_INTERVAL_MS = 20000;

class SaveFailed extends Error {}

export class Client {
  private state: State;
  private name: string | null;
  private outbox: OutboxEntry[];
  private readonly seen = new Set<string>();
  private inFlight = false;

  private ws: WebSocket | null = null;
  private wsOpen = false;
  private loginName = "";
  /** True while going online for /login: failure returns to idle and login_ok saves the name. */
  private loginMode = false;
  private connectTimer: NodeJS.Timeout | null = null;
  private pingTimer: NodeJS.Timeout | null = null;

  private readonly queue: QueueEvent[] = [];
  private pumping = false;
  private finished = false;

  constructor(private readonly opts: ClientOptions) {
    this.name = opts.saved.name;
    this.outbox = opts.saved.outbox.map((m) => ({ ...m }));
    this.state = this.name === null ? "idle" : "offline";
  }

  /** Startup: with a saved name, go online as if /online was typed. */
  start(): void {
    if (this.name !== null) this.run(() => this.goOnline(this.name as string));
  }

  line(line: string): void {
    this.push({ kind: "line", line });
  }

  eof(): void {
    this.push({ kind: "eof" });
  }

  // ---- event queue -------------------------------------------------------

  private push(ev: QueueEvent): void {
    if (this.finished) return;
    this.queue.push(ev);
    this.pump();
  }

  private take(): QueueEvent | undefined {
    if (this.state === "connecting") {
      // Going online holds commands up: only connection events are handled meanwhile.
      const i = this.queue.findIndex((e) => e.kind !== "line" && e.kind !== "eof");
      return i < 0 ? undefined : this.queue.splice(i, 1)[0];
    }
    return this.queue.shift();
  }

  private pump(): void {
    if (this.pumping) return;
    this.pumping = true;
    try {
      while (!this.finished) {
        const ev = this.take();
        if (ev === undefined) break;
        this.run(() => this.handle(ev));
      }
    } finally {
      this.pumping = false;
    }
  }

  private run(fn: () => void): void {
    try {
      fn();
    } catch (e) {
      if (e instanceof SaveFailed) {
        this.finished = true;
        this.queue.length = 0;
        this.dropConnection();
        this.opts.onFatal(e.message);
      } else {
        console.error("internal error:", e);
      }
    }
  }

  private handle(ev: QueueEvent): void {
    switch (ev.kind) {
      case "line":
        return this.handleLine(ev.line);
      case "eof":
        return this.quit();
      case "open":
        return this.handleOpen(ev.ws);
      case "message":
        return this.handleMessage(ev.ws, ev.data);
      case "close":
        return this.handleClose(ev.ws);
      case "ws_error":
      case "connect_timeout":
        if (ev.ws === this.ws && this.state === "connecting" && !this.wsOpen) this.connectFailed();
        return;
    }
  }

  // ---- output and saving -------------------------------------------------

  private print(ev: OutEvent): void {
    this.opts.write(formatLine(ev, this.opts.machine));
  }

  private error(code: string, message: string, ref?: string): void {
    this.print(ref === undefined ? { kind: "ERROR", code, message } : { kind: "ERROR", code, ref, message });
  }

  private save(): void {
    try {
      saveState(this.opts.dataDir, { name: this.name, outbox: this.outbox });
    } catch (e) {
      throw new SaveFailed(`cannot save state in ${this.opts.dataDir}: ${(e as Error).message}`);
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
      case "usage":
        return this.error("usage", cmd.message);
      case "quit":
        return this.quit();
      case "login":
        if (this.state !== "idle") return this.error("already_logged_in", "already logged in");
        this.loginMode = true;
        return this.goOnline(cmd.name);
      case "online":
        if (this.state === "idle") return this.notLoggedIn();
        if (this.state === "online") return this.error("already_online", "already online");
        return this.goOnline(this.name as string);
      case "offline":
        if (this.state === "idle") return this.notLoggedIn();
        if (this.state === "offline") return this.error("already_offline", "already offline");
        this.dropConnection();
        this.state = "offline";
        return this.print({ kind: "OFFLINE" });
      case "send": {
        if (this.state === "idle") return this.notLoggedIn();
        if (Buffer.byteLength(cmd.text, "utf8") > MAX_TEXT_BYTES) {
          return this.error("too_long", "message too long (max 8192 bytes)");
        }
        const msg: OutboxEntry = { id: randomUUID(), to: cmd.to, text: cmd.text };
        this.outbox.push(msg);
        this.save();
        this.print({ kind: "QUEUED", id: msg.id, to: msg.to, text: msg.text });
        return this.sendNext();
      }
    }
  }

  private notLoggedIn(): void {
    this.error("not_logged_in", "log in first with /login <name>");
  }

  private quit(): void {
    this.print({ kind: "BYE" });
    this.finished = true;
    this.queue.length = 0;
    this.dropConnection();
    this.opts.onQuit();
  }

  // ---- connection --------------------------------------------------------

  private goOnline(name: string): void {
    this.state = "connecting";
    this.loginName = name;
    this.wsOpen = false;
    let ws: WebSocket;
    try {
      ws = new WebSocket(this.opts.server, { maxPayload: 64 * 1024, handshakeTimeout: CONNECT_TIMEOUT_MS });
    } catch {
      this.connectFailed();
      return;
    }
    this.ws = ws;
    ws.on("open", () => this.push({ kind: "open", ws }));
    ws.on("message", (data: WebSocket.RawData, isBinary: boolean) => {
      if (isBinary) return;
      const buf = Array.isArray(data) ? Buffer.concat(data) : Buffer.from(data as ArrayBuffer);
      this.push({ kind: "message", ws, data: buf.toString("utf8") });
    });
    ws.on("close", () => this.push({ kind: "close", ws }));
    ws.on("error", () => this.push({ kind: "ws_error", ws }));
    this.connectTimer = setTimeout(() => this.push({ kind: "connect_timeout", ws }), CONNECT_TIMEOUT_MS);
  }

  /** The state a failed going-online returns to. */
  private failState(): State {
    return this.loginMode ? "idle" : "offline";
  }

  private connectFailed(): void {
    this.dropConnection();
    this.state = this.failState();
    this.loginMode = false;
    this.error("connect_failed", `cannot connect to ${this.opts.server}`);
  }

  private clearTimers(): void {
    if (this.connectTimer !== null) clearTimeout(this.connectTimer);
    if (this.pingTimer !== null) clearInterval(this.pingTimer);
    this.connectTimer = null;
    this.pingTimer = null;
  }

  /** Closes the current connection on purpose; anything still arriving from it is ignored. */
  private dropConnection(): void {
    this.clearTimers();
    const ws = this.ws;
    this.ws = null;
    this.wsOpen = false;
    this.inFlight = false;
    if (ws === null) return;
    try {
      if (ws.readyState === WebSocket.CONNECTING) ws.terminate();
      else ws.close();
    } catch (e) {
      console.error("close failed:", e);
    }
  }

  private handleOpen(ws: WebSocket): void {
    if (ws !== this.ws || this.state !== "connecting") return;
    this.wsOpen = true;
    if (this.connectTimer !== null) clearTimeout(this.connectTimer);
    this.connectTimer = null;
    this.startKeepAlive(ws);
    ws.send(JSON.stringify({ type: "login", name: this.loginName }));
  }

  private startKeepAlive(ws: WebSocket): void {
    let awaitingPong = false;
    ws.on("pong", () => {
      awaitingPong = false;
    });
    this.pingTimer = setInterval(() => {
      if (awaitingPong) {
        ws.terminate(); // produces "close", handled as a disconnection
        return;
      }
      awaitingPong = true;
      try {
        ws.ping();
      } catch (e) {
        console.error("ping failed:", e);
      }
    }, PING_INTERVAL_MS);
  }

  private handleClose(ws: WebSocket): void {
    if (ws !== this.ws) return;
    const wasOpen = this.wsOpen;
    this.clearTimers();
    this.ws = null;
    this.wsOpen = false;
    this.inFlight = false;
    if (this.state === "connecting") {
      if (!wasOpen) {
        this.state = this.failState();
        this.loginMode = false;
        this.error("connect_failed", `cannot connect to ${this.opts.server}`);
        return;
      }
      this.state = this.failState();
      this.loginMode = false;
      this.print({ kind: "DISCONNECTED" });
    } else if (this.state === "online") {
      this.state = "offline";
      this.print({ kind: "DISCONNECTED" });
    }
  }

  private handleMessage(ws: WebSocket, data: string): void {
    if (ws !== this.ws) return;
    const frame = parseServerFrame(data);
    if (frame === null) return;
    if (this.state === "connecting") this.handleLoginAnswer(frame);
    else if (this.state === "online") this.handleOnlineFrame(frame);
  }

  private handleLoginAnswer(frame: ServerFrame): void {
    if (frame.type === "login_ok") {
      if (this.loginMode) {
        this.name = frame.name;
        this.save();
        this.loginMode = false;
      }
      this.state = "online";
      this.print({ kind: "LOGGED_IN", name: frame.name });
      this.sendNext();
    } else if (frame.type === "error") {
      this.error(frame.code, frame.message, frame.ref);
      this.dropConnection();
      this.state = this.failState();
      this.loginMode = false;
    }
  }

  private handleOnlineFrame(frame: ServerFrame): void {
    switch (frame.type) {
      case "ack": {
        if (!this.inFlight || frame.id !== this.outbox[0].id) return;
        const msg = this.outbox.shift() as OutboxEntry;
        this.inFlight = false;
        this.save();
        this.print({ kind: "SENT", id: msg.id, seq: frame.seq, to: msg.to });
        return this.sendNext();
      }
      case "error": {
        if (frame.ref !== undefined && this.inFlight && frame.ref === this.outbox[0].id) {
          this.outbox.shift();
          this.inFlight = false;
          this.save();
          this.error(frame.code, frame.message, frame.ref);
          return this.sendNext();
        }
        return this.error(frame.code, frame.message, frame.ref);
      }
      case "deliver": {
        const key = JSON.stringify([frame.from, frame.id]);
        if (!this.seen.has(key)) {
          this.seen.add(key);
          this.print({ kind: "RECV", seq: frame.seq, id: frame.id, from: frame.from, text: frame.text });
        }
        (this.ws as WebSocket).send(JSON.stringify({ type: "deliver_ack", seq: frame.seq }));
        return;
      }
      case "login_ok":
        return;
    }
  }

  private sendNext(): void {
    if (this.state !== "online" || this.inFlight || this.outbox.length === 0 || this.ws === null) return;
    const msg = this.outbox[0];
    this.ws.send(JSON.stringify({ type: "send", id: msg.id, to: msg.to, text: msg.text }));
    this.inFlight = true;
  }
}
