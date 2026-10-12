// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { loadState, parseState, saveState } from "../storage.js";

const id1 = "0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11";
const id2 = "5d2e8a90-7c1b-4f3e-8d6a-2b9c4e1f0a77";
const enc = (s: string) => new TextEncoder().encode(s);
const valid = (v: unknown) => parseState(enc(JSON.stringify(v))).ok;

test("valid files", () => {
  assert.equal(valid({ version: 1, name: null, outbox: [] }), true);
  assert.equal(valid({ version: 1, name: "alice", outbox: [{ id: id1, to: "bob", text: "hi" }] }), true);
  assert.equal(parseState(enc('{"version":1.0,"name":"a","outbox":[]}')).ok, true);
  const r = parseState(enc(JSON.stringify({ version: 1, name: "a", extra: 1, outbox: [{ id: id1, to: "b", text: "t", x: 2 }] })));
  assert.deepEqual(r, { ok: true, state: { name: "a", outbox: [{ id: id1, to: "b", text: "t" }] } });
  assert.equal(valid({ version: 1, name: "a", outbox: [{ id: id1, to: "b", text: "é".repeat(4096) }] }), true);
});

test("rule 1: UTF-8 JSON object, no BOM", () => {
  assert.equal(parseState(enc("not json")).ok, false);
  assert.equal(parseState(enc("[]")).ok, false);
  assert.equal(parseState(enc("null")).ok, false);
  assert.equal(parseState(new Uint8Array([0xef, 0xbb, 0xbf, ...enc('{"version":1,"name":null,"outbox":[]}')])).ok, false);
  assert.equal(parseState(new Uint8Array([...enc('{"version":1,"name":"'), 0xff, ...enc('","outbox":[]}')])).ok, false);
});

test("rule 2: version", () => {
  assert.equal(valid({ name: null, outbox: [] }), false);
  assert.equal(valid({ version: true, name: null, outbox: [] }), false);
  assert.equal(valid({ version: "1", name: null, outbox: [] }), false);
  assert.equal(valid({ version: 2, name: null, outbox: [] }), false);
});

test("rule 3: name", () => {
  assert.equal(valid({ version: 1, outbox: [] }), false);
  assert.equal(valid({ version: 1, name: "", outbox: [] }), false);
  assert.equal(valid({ version: 1, name: 5, outbox: [] }), false);
});

test("rule 4: outbox", () => {
  assert.equal(valid({ version: 1, name: "a" }), false);
  assert.equal(valid({ version: 1, name: "a", outbox: {} }), false);
  assert.equal(valid({ version: 1, name: null, outbox: [{ id: id1, to: "b", text: "t" }] }), false);
});

test("rule 5: entries", () => {
  const e = (x: unknown) => valid({ version: 1, name: "a", outbox: [x] });
  assert.equal(e("str"), false);
  assert.equal(e({ to: "b", text: "t" }), false);
  assert.equal(e({ id: id1.toUpperCase(), to: "b", text: "t" }), false);
  assert.equal(e({ id: "nope", to: "b", text: "t" }), false);
  assert.equal(e({ id: id1, to: "", text: "t" }), false);
  assert.equal(e({ id: id1, to: 1, text: "t" }), false);
  assert.equal(e({ id: id1, to: "b", text: "" }), false);
  assert.equal(e({ id: id1, to: "b" }), false);
  assert.equal(e({ id: id1, to: "b", text: "x".repeat(8193) }), false);
});

test("rule 6: unique ids", () => {
  const m = { id: id1, to: "b", text: "t" };
  assert.equal(valid({ version: 1, name: "a", outbox: [m, m] }), false);
  assert.equal(valid({ version: 1, name: "a", outbox: [m, { ...m, id: id2 }] }), true);
});

test("save and load round trip; missing file", () => {
  const dir = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "msg-")), "a", "b");
  assert.deepEqual(loadState(dir), { name: null, outbox: [] });
  assert.equal(fs.existsSync(dir), false);
  const state = { name: "alice", outbox: [{ id: id1, to: "bob", text: "hi " }] };
  saveState(dir, state);
  assert.deepEqual(loadState(dir), state);
  assert.equal(fs.existsSync(path.join(dir, "state.json.tmp")), false);
  fs.writeFileSync(path.join(dir, "state.json"), "{");
  assert.throws(() => loadState(dir));
});
