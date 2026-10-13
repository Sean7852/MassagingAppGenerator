// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import * as fs from "node:fs";
import * as path from "node:path";

export interface OutboxEntry {
  id: string;
  to: string;
  text: string;
}

export const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
export const MAX_TEXT_BYTES = 8192;

/**
 * Validates the raw bytes of a state file (40-storage.md § What makes the file valid).
 * Returns the outbox, or an error string.
 */
export function parseState(bytes: Uint8Array): OutboxEntry[] | { error: string } {
  let text: string;
  try {
    text = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes);
  } catch {
    return { error: "not valid UTF-8" };
  }
  if (text.startsWith("﻿")) return { error: "starts with a byte order mark" };
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return { error: "not valid JSON" };
  }
  if (typeof data !== "object" || data === null || Array.isArray(data)) {
    return { error: "top level is not an object" };
  }
  const obj = data as Record<string, unknown>;
  if (obj.version !== 2) return { error: "version is not 2" };
  if (!Array.isArray(obj.outbox)) return { error: "outbox is not an array" };
  const out: OutboxEntry[] = [];
  const ids = new Set<string>();
  for (const e of obj.outbox as unknown[]) {
    if (typeof e !== "object" || e === null || Array.isArray(e)) {
      return { error: "outbox entry is not an object" };
    }
    const r = e as Record<string, unknown>;
    if (typeof r.id !== "string" || !UUID_RE.test(r.id)) return { error: "outbox entry has a bad id" };
    if (typeof r.to !== "string" || r.to === "") return { error: "outbox entry has a bad to" };
    if (typeof r.text !== "string" || r.text === "" || Buffer.byteLength(r.text, "utf8") > MAX_TEXT_BYTES) {
      return { error: "outbox entry has a bad text" };
    }
    if (ids.has(r.id)) return { error: "duplicate id in outbox" };
    ids.add(r.id);
    out.push({ id: r.id, to: r.to, text: r.text });
  }
  return out;
}

export function userDir(dataDir: string, name: string): string {
  return path.join(dataDir, name);
}

/** Loads a user's outbox. Throws an Error with a description when it cannot be loaded. */
export function loadOutbox(dataDir: string, name: string): OutboxEntry[] {
  const file = path.join(userDir(dataDir, name), "state.json");
  let bytes: Buffer;
  try {
    bytes = fs.readFileSync(file);
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") return [];
    throw new Error(`cannot read ${file}: ${(err as Error).message}`);
  }
  const res = parseState(bytes);
  if (!Array.isArray(res)) throw new Error(`invalid state file ${file}: ${res.error}`);
  return res;
}

/** Saves a user's outbox atomically. Throws on failure. */
export function saveOutbox(dataDir: string, name: string, outbox: OutboxEntry[]): void {
  const dir = userDir(dataDir, name);
  const file = path.join(dir, "state.json");
  const tmp = path.join(dir, "state.json.tmp");
  const state = { version: 2, outbox: outbox.map((m) => ({ id: m.id, to: m.to, text: m.text })) };
  fs.mkdirSync(dir, { recursive: true });
  const fd = fs.openSync(tmp, "w");
  try {
    fs.writeSync(fd, JSON.stringify(state));
    fs.fsyncSync(fd);
  } finally {
    fs.closeSync(fd);
  }
  fs.renameSync(tmp, file);
}
