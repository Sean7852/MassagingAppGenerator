// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import * as fs from "node:fs";
import * as path from "node:path";

export interface OutboxEntry {
  id: string;
  to: string;
  text: string;
}

export interface State {
  name: string | null;
  outbox: OutboxEntry[];
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/** Validates the raw bytes of a state file (40-storage.md). Returns the state or an error. */
export function parseState(bytes: Uint8Array): { ok: true; state: State } | { ok: false; error: string } {
  if (bytes.length >= 3 && bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf) {
    return { ok: false, error: "state file starts with a byte order mark" };
  }
  let text: string;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    return { ok: false, error: "state file is not valid UTF-8" };
  }
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return { ok: false, error: "state file is not valid JSON" };
  }
  if (!isObject(data)) return { ok: false, error: "state file is not a JSON object" };
  if (!("version" in data) || data.version !== 1) return { ok: false, error: "version must be 1" };
  if (!("name" in data)) return { ok: false, error: "name is missing" };
  const name = data.name;
  if (name !== null && (typeof name !== "string" || name === "")) {
    return { ok: false, error: "name must be null or a non-empty string" };
  }
  if (!("outbox" in data) || !Array.isArray(data.outbox)) return { ok: false, error: "outbox must be an array" };
  if (name === null && data.outbox.length > 0) return { ok: false, error: "outbox must be empty without a name" };
  const outbox: OutboxEntry[] = [];
  const ids = new Set<string>();
  for (const e of data.outbox as unknown[]) {
    if (!isObject(e)) return { ok: false, error: "outbox entry is not an object" };
    const { id, to, text: t } = e;
    if (typeof id !== "string" || !UUID_RE.test(id)) return { ok: false, error: "outbox entry has a bad id" };
    if (typeof to !== "string" || to === "") return { ok: false, error: "outbox entry has a bad to" };
    if (typeof t !== "string" || t === "" || Buffer.byteLength(t, "utf8") > 8192) {
      return { ok: false, error: "outbox entry has a bad text" };
    }
    if (ids.has(id)) return { ok: false, error: "outbox has a duplicate id" };
    ids.add(id);
    outbox.push({ id, to, text: t });
  }
  return { ok: true, state: { name, outbox } };
}

export function stateFile(dataDir: string): string {
  return path.join(dataDir, "state.json");
}

/** Loads the saved state. Throws an Error with a message if it cannot be used. */
export function loadState(dataDir: string): State {
  const file = stateFile(dataDir);
  let bytes: Buffer;
  try {
    bytes = fs.readFileSync(file);
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") return { name: null, outbox: [] };
    throw new Error(`cannot read ${file}: ${(e as Error).message}`);
  }
  const r = parseState(bytes);
  if (!r.ok) throw new Error(`invalid ${file}: ${r.error}`);
  return r.state;
}

/** Saves the state atomically: write tmp, fsync, rename. Throws on failure. */
export function saveState(dataDir: string, state: State): void {
  fs.mkdirSync(dataDir, { recursive: true });
  const file = stateFile(dataDir);
  const tmp = file + ".tmp";
  const content = JSON.stringify({
    version: 1,
    name: state.name,
    outbox: state.outbox.map((m) => ({ id: m.id, to: m.to, text: m.text })),
  });
  const fd = fs.openSync(tmp, "w");
  try {
    fs.writeSync(fd, content);
    fs.fsyncSync(fd);
  } finally {
    fs.closeSync(fd);
  }
  fs.renameSync(tmp, file);
}
