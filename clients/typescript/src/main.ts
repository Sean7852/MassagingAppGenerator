// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import * as readline from "node:readline";
import { parseArgs } from "node:util";
import WebSocket from "ws";
import { Client, type ClientEvent, type Conn } from "./client.js";
import { writeLine } from "./output.js";

const DEFAULT_URL = "ws://127.0.0.1:8765";
const USAGE = "usage: node dist/main.js [--server <url>]";

function parseServerUrl(): string | null {
  try {
    const { values } = parseArgs({
      args: process.argv.slice(2),
      options: { server: { type: "string" } },
      allowPositionals: false,
      strict: true,
    });
    return values.server ?? DEFAULT_URL;
  } catch {
    return null;
  }
}

function connectWs(url: string, emit: (event: ClientEvent) => void): Conn {
  const ws = new WebSocket(url, { maxPayload: 64 * 1024, handshakeTimeout: 5000 });
  const conn: Conn = {
    send: (data) => ws.send(data),
    close: () => ws.close(),
  };
  ws.on("open", () => emit({ kind: "open", conn }));
  ws.on("message", (data: WebSocket.RawData, isBinary: boolean) => {
    if (isBinary) return;
    const text = Array.isArray(data)
      ? Buffer.concat(data).toString("utf8")
      : Buffer.from(data as Buffer).toString("utf8");
    emit({ kind: "message", conn, data: text });
  });
  ws.on("error", (err) => {
    console.error("websocket error:", err.message);
    emit({ kind: "error", conn });
  });
  ws.on("close", () => emit({ kind: "close", conn }));
  return conn;
}

async function main(): Promise<void> {
  const url = parseServerUrl();
  if (url === null) {
    process.stderr.write(USAGE + "\n");
    process.exitCode = 2;
    return;
  }

  // One queue for stdin lines and WebSocket events, drained by one loop.
  const events: ClientEvent[] = [];
  let wake: (() => void) | null = null;
  const emit = (event: ClientEvent): void => {
    events.push(event);
    if (wake) {
      const w = wake;
      wake = null;
      w();
    }
  };

  const client = new Client(url, connectWs, emit, writeLine);

  process.stdin.setEncoding("utf8");
  const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity, terminal: false });
  rl.on("line", (line) => emit({ kind: "line", line }));
  rl.on("close", () => emit({ kind: "eof" }));

  while (!client.finished) {
    const event = events.shift();
    if (event === undefined) {
      await new Promise<void>((resolve) => {
        wake = resolve;
      });
      continue;
    }
    try {
      client.handle(event);
    } catch (err) {
      console.error("internal error:", err);
    }
  }

  rl.close();
  process.stdin.pause();
  process.exitCode = 0;
}

main().catch((err) => {
  console.error("fatal:", err);
});
