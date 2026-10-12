// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { loadState, parseStateBytes, saveState, validateState } from "../storage.js";

const ID = "0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11";
const ID2 = "5d2e8a90-7c1b-4f3e-8d6a-2b9c4e1f0a77";
const entry = (over: Record<string, unknown> = {}) => ({ id: ID, to: "bob", text: "hi", ...over });
const valid = (raw: unknown) => !("error" in validateState(raw));

test("valid files", () => {
  assert.ok(valid({ version: 1, name: null, outbox: [] }));
  assert.ok(valid({ version: 1.0, name: "alice", outbox: [entry(), entry({ id: ID2 })], extra: 1 }));
  assert.ok(valid({ version: 1, name: "alice", outbox: [entry({ extra: true, text: "é".repeat(4096) })] }));
  assert.deepEqual(validateState({ version: 1, name: "a", outbox: [entry({ x: 1 })] }), {
    name: "a",
    outbox: [{ id: ID, to: "bob", text: "hi" }],
  });
});

test("rule 1: UTF-8 JSON object without BOM", () => {
  const ok = Buffer.from(JSON.stringify({ version: 1, name: null, outbox: [] }));
  assert.ok(!("error" in parseStateBytes(ok)));
  assert.ok("error" in parseStateBytes(Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), ok])));
  assert.ok("error" in parseStateBytes(Buffer.from([0x7b, 0xff, 0x7d])));
  assert.ok("error" in parseStateBytes(Buffer.from("not json")));
  assert.ok("error" in parseStateBytes(Buffer.from("[]")));
  assert.ok(!valid(null));
  assert.ok(!valid("x"));
});

test("rule 2: version", () => {
  for (const v of [true, "1", 2, null, undefined]) assert.ok(!valid({ version: v, name: null, outbox: [] }));
  assert.ok(!valid({ name: null, outbox: [] }));
});

test("rule 3: name", () => {
  for (const n of ["", 1, false]) assert.ok(!valid({ version: 1, name: n, outbox: [] }));
  assert.ok(!valid({ version: 1, outbox: [] }));
});

test("rule 4: outbox", () => {
  assert.ok(!valid({ version: 1, name: "a" }));
  assert.ok(!valid({ version: 1, name: "a", outbox: {} }));
  assert.ok(!valid({ version: 1, name: null, outbox: [entry()] }));
});

test("rule 5: entries", () => {
  const bad = [
    null,
    [],
    "x",
    entry({ id: ID.toUpperCase() }),
    entry({ id: "abc" }),
    entry({ id: 5 }),
    entry({ id: undefined }),
    entry({ to: "" }),
    entry({ to: 1 }),
    entry({ to: undefined }),
    entry({ text: "" }),
    entry({ text: 1 }),
    entry({ text: undefined }),
    entry({ text: "x".repeat(8193) }),
    entry({ text: "é".repeat(4096) + "x" }),
  ];
  for (const e of bad) assert.ok(!valid({ version: 1, name: "a", outbox: [e] }), JSON.stringify(e));
});

test("rule 6: unique ids", () => {
  assert.ok(!valid({ version: 1, name: "a", outbox: [entry(), entry({ text: "other" })] }));
});

test("save and load round trip", () => {
  const dir = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "msgtest-")), "a", "b");
  assert.deepEqual(loadState(dir), { name: null, outbox: [] });
  assert.ok(!fs.existsSync(dir));
  const state = { name: "alice", outbox: [{ id: ID, to: "bob", text: "x 👋" }] };
  saveState(dir, state);
  assert.deepEqual(loadState(dir), state);
  assert.ok(!fs.existsSync(path.join(dir, "state.json.tmp")));
  const raw = JSON.parse(fs.readFileSync(path.join(dir, "state.json"), "utf8"));
  assert.equal(raw.version, 1);
});

test("invalid file is reported and left untouched", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "msgtest-"));
  const file = path.join(dir, "state.json");
  fs.writeFileSync(file, '{"version":"1"}');
  assert.ok("error" in loadState(dir));
  assert.equal(fs.readFileSync(file, "utf8"), '{"version":"1"}');
});
