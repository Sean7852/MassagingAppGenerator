// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import * as fs from "node:fs";
import * as path from "node:path";

export interface OutboxEntry {
  id: string;
  to: string;
  text: string;
}

export interface SavedState {
  name: string | null;
  outbox: OutboxEntry[];
}

export const MAX_TEXT_BYTES = 8192;
const ID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function nonEmptyString(v: unknown): v is string {
  return typeof v === "string" && v.length > 0;
}

/** Checks the rules of 40-storage.md § What makes the file valid. Returns an error string if invalid. */
export function parseStateBytes(bytes: Uint8Array): SavedState | { error: string } {
  if (bytes.length >= 3 && bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf) {
    return { error: "state file starts with a byte order mark" };
  }
  let text: string;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    return { error: "state file is not valid UTF-8" };
  }
  let raw: unknown;
  try {
    raw = JSON.parse(text);
  } catch {
    return { error: "state file is not valid JSON" };
  }
  return validateState(raw);
}

export function validateState(raw: unknown): SavedState | { error: string } {
  if (!isObject(raw)) return { error: "top level is not an object" };
  if (!("version" in raw) || typeof raw.version !== "number" || raw.version !== 1) {
    return { error: "version is not the number 1" };
  }
  if (!("name" in raw) || !(raw.name === null || nonEmptyString(raw.name))) {
    return { error: "name is not null or a non-empty string" };
  }
  if (!("outbox" in raw) || !Array.isArray(raw.outbox)) return { error: "outbox is not an array" };
  const name = raw.name as string | null;
  if (name === null && raw.outbox.length > 0) return { error: "outbox is not empty but name is null" };
  const outbox: OutboxEntry[] = [];
  const ids = new Set<string>();
  for (const e of raw.outbox as unknown[]) {
    if (!isObject(e)) return { error: "outbox entry is not an object" };
    if (typeof e.id !== "string" || !ID_RE.test(e.id)) return { error: "outbox entry has a bad id" };
    if (!nonEmptyString(e.to)) return { error: "outbox entry has a bad to" };
    if (!nonEmptyString(e.text) || Buffer.byteLength(e.text, "utf8") > MAX_TEXT_BYTES) {
      return { error: "outbox entry has a bad text" };
    }
    if (ids.has(e.id)) return { error: "outbox has a repeated id" };
    ids.add(e.id);
    outbox.push({ id: e.id, to: e.to, text: e.text });
  }
  return { name, outbox };
}

export function stateFile(dataDir: string): string {
  return path.join(dataDir, "state.json");
}

/** Loads the saved state; a missing file means no name and an empty outbox. */
export function loadState(dataDir: string): SavedState | { error: string } {
  let bytes: Buffer;
  try {
    bytes = fs.readFileSync(stateFile(dataDir));
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") return { name: null, outbox: [] };
    return { error: `cannot read ${stateFile(dataDir)}: ${(e as Error).message}` };
  }
  const result = parseStateBytes(bytes);
  if ("error" in result) return { error: `invalid ${stateFile(dataDir)}: ${result.error}` };
  return result;
}

/** Saves atomically (write tmp, fsync, rename). Throws on failure. */
export function saveState(dataDir: string, state: SavedState): void {
  const file = stateFile(dataDir);
  const tmp = file + ".tmp";
  const data = {
    version: 1,
    name: state.name,
    outbox: state.outbox.map((m) => ({ id: m.id, to: m.to, text: m.text })),
  };
  fs.mkdirSync(dataDir, { recursive: true });
  const fd = fs.openSync(tmp, "w");
  try {
    fs.writeSync(fd, JSON.stringify(data));
    fs.fsyncSync(fd);
  } finally {
    fs.closeSync(fd);
  }
  fs.renameSync(tmp, file);
}
