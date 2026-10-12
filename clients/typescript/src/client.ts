// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { randomUUID } from "node:crypto";
import { parseLine } from "./commands.js";
import { errorLine, loggedInLine, recvLine, sentLine } from "./output.js";

/** A connection as the client sees it. */
export interface Conn {
  send(data: string): void;
  close(): void;
}

/** Everything the client reacts to, handled one at a time. */
export type ClientEvent =
  | { kind: "line"; line: string }
  | { kind: "eof" }
  | { kind: "open"; conn: Conn }
  | { kind: "message"; conn: Conn; data: string }
  | { kind: "error"; conn: Conn }
  | { kind: "close"; conn: Conn };

/** Opens a connection; events for it are delivered back through `emit`. May throw. */
export type Connector = (url: string, emit: (event: ClientEvent) => void) => Conn;

type State = "idle" | "connecting" | "online";

interface Queued {
  id: string;
  to: string;
  text: string;
}

type Frame = Record<string, unknown>;

function isSeq(v: unknown): v is number {
  return typeof v === "number" && Number.isInteger(v);
}

export class Client {
  private state: State = "idle";
  private conn: Conn | null = null;
  private opened = false;
  private readonly queue: Queued[] = [];
  private inFlight = false;
  private readonly seen = new Set<string>();
  /** True once BYE was printed; nothing is handled after that. */
  finished = false;

  constructor(
    private readonly url: string,
    private readonly connector: Connector,
    private readonly emit: (event: ClientEvent) => void,
    private readonly out: (line: string) => void,
    private readonly newId: () => string = randomUUID,
  ) {}

  handle(event: ClientEvent): void {
    if (this.finished) return;
    switch (event.kind) {
      case "line":
        return this.onLine(event.line);
      case "eof":
        return this.quit();
      case "open":
        return this.onOpen(event.conn);
      case "message":
        return this.onMessage(event.conn, event.data);
      case "error":
        return this.onError(event.conn);
      case "close":
        return this.onClose(event.conn);
    }
  }

  // ---- user commands ----

  private onLine(line: string): void {
    const cmd = parseLine(line);
    switch (cmd.kind) {
      case "empty":
        return;
      case "login":
        return this.login(cmd.name);
      case "send":
        return this.send(cmd.to, cmd.text);
      case "quit":
        return this.quit();
      case "usage":
        return this.out(errorLine("usage", cmd.message));
      case "unknown":
        return this.out(errorLine("unknown_command", "unknown command"));
    }
  }

  private login(name: string): void {
    if (this.state !== "idle") {
      this.out(errorLine("already_logged_in", "already logged in or connecting"));
      return;
    }
    this.state = "connecting";
    this.opened = false;
    this.pendingName = name;
    try {
      this.conn = this.connector(this.url, this.emit);
    } catch {
      this.connectFailed();
    }
  }

  private pendingName = "";

  private send(to: string, text: string): void {
    if (this.state !== "online") {
      this.out(errorLine("not_logged_in", "log in first with /login <name>"));
      return;
    }
    this.queue.push({ id: this.newId(), to, text });
    this.pump();
  }

  private quit(): void {
    this.out("BYE");
    this.finished = true;
    this.queue.length = 0;
    this.inFlight = false;
    this.dropConnection();
    this.state = "idle";
  }

  // ---- connection events ----

  private onOpen(conn: Conn): void {
    if (conn !== this.conn || this.state !== "connecting") return;
    this.opened = true;
    this.write({ type: "login", name: this.pendingName });
  }

  private onError(conn: Conn): void {
    if (conn !== this.conn) return;
    // After open, a close event always follows an error; handle it there.
    if (!this.opened) this.connectFailed();
  }

  private onClose(conn: Conn): void {
    if (conn !== this.conn) return;
    if (!this.opened) {
      this.connectFailed();
      return;
    }
    this.conn = null;
    if (this.state === "online") {
      for (const m of this.queue) {
        this.out(
          errorLine("not_sent", "connection lost before the server acknowledged the message", m.id),
        );
      }
      this.queue.length = 0;
      this.inFlight = false;
    }
    this.out("DISCONNECTED");
    this.state = "idle";
  }

  private onMessage(conn: Conn, data: string): void {
    if (conn !== this.conn) return;
    let frame: unknown;
    try {
      frame = JSON.parse(data);
    } catch {
      return;
    }
    if (typeof frame !== "object" || frame === null || Array.isArray(frame)) return;
    const f = frame as Frame;
    switch (f.type) {
      case "login_ok":
        return this.onLoginOk(f);
      case "ack":
        return this.onAck(f);
      case "deliver":
        return this.onDeliver(f);
      case "error":
        return this.onServerError(f);
      default:
        return;
    }
  }

  private onLoginOk(f: Frame): void {
    if (this.state !== "connecting" || typeof f.name !== "string") return;
    this.state = "online";
    this.out(loggedInLine(f.name));
    this.pump();
  }

  private onAck(f: Frame): void {
    if (this.state !== "online" || !this.inFlight) return;
    if (typeof f.id !== "string" || !isSeq(f.seq)) return;
    const head = this.queue[0];
    if (f.id !== head.id) return;
    this.queue.shift();
    this.inFlight = false;
    this.out(sentLine(head.id, f.seq, head.to));
    this.pump();
  }

  private onDeliver(f: Frame): void {
    if (this.state !== "online") return;
    if (
      !isSeq(f.seq) ||
      typeof f.id !== "string" ||
      typeof f.from !== "string" ||
      typeof f.text !== "string"
    ) {
      return;
    }
    const key = JSON.stringify([f.from, f.id]);
    if (!this.seen.has(key)) {
      this.seen.add(key);
      this.out(recvLine(f.seq, f.id, f.from, f.text));
    }
    this.write({ type: "deliver_ack", seq: f.seq });
  }

  private onServerError(f: Frame): void {
    if (typeof f.code !== "string" || typeof f.message !== "string") return;
    const ref = typeof f.ref === "string" ? f.ref : undefined;
    this.out(errorLine(f.code, f.message, ref));
    if (this.state === "connecting") {
      this.dropConnection();
      this.state = "idle";
      return;
    }
    if (this.state === "online" && this.inFlight && ref !== undefined && ref === this.queue[0].id) {
      this.queue.shift();
      this.inFlight = false;
      this.pump();
    }
  }

  // ---- helpers ----

  private pump(): void {
    if (this.state !== "online" || this.inFlight || this.queue.length === 0) return;
    const m = this.queue[0];
    this.inFlight = true;
    this.write({ type: "send", id: m.id, to: m.to, text: m.text });
  }

  private write(frame: Frame): void {
    if (this.conn === null) return;
    try {
      this.conn.send(JSON.stringify(frame));
    } catch (err) {
      console.error("send failed:", err);
    }
  }

  private connectFailed(): void {
    this.dropConnection();
    this.state = "idle";
    this.out(errorLine("connect_failed", `cannot connect to ${this.url}`));
  }

  /** Closes the connection on purpose; its later events are ignored. */
  private dropConnection(): void {
    const conn = this.conn;
    this.conn = null;
    this.opened = false;
    if (conn === null) return;
    try {
      conn.close();
    } catch (err) {
      console.error("close failed:", err);
    }
  }
}
