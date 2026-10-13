// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { parseState, loadOutbox, saveOutbox } from "../storage.js";

const ID = "0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11";
const ID2 = "5d2e8a90-7c1b-4f3e-8d6a-2b9c4e1f0a77";
const enc = (s: string) => new TextEncoder().encode(s);
const ok = (s: string | Uint8Array) => Array.isArray(parseState(typeof s === "string" ? enc(s) : s));
const st = (outbox: unknown, extra = "") => `{"version":2${extra},"outbox":${JSON.stringify(outbox)}}`;

test("valid files", () => {
  assert.deepEqual(parseState(enc(st([]))), []);
  assert.deepEqual(parseState(enc(st([{ id: ID, to: "bob", text: "hi", x: 1 }], ',"extra":true'))), [
    { id: ID, to: "bob", text: "hi" },
  ]);
  assert.ok(ok(`{"version":2.0,"outbox":[]}`));
  assert.ok(ok(st([{ id: ID, to: "Bob!", text: "é".repeat(4096) }])));
});

test("rule 1: UTF-8 JSON object without BOM", () => {
  assert.ok(!ok(new Uint8Array([0xef, 0xbb, 0xbf, ...enc(st([]))])));
  assert.ok(!ok(new Uint8Array([...enc('{"version":2,"outbox":[],"x":"'), 0xff, ...enc('"}')])));
  assert.ok(!ok("not json"));
  assert.ok(!ok("[]"));
  assert.ok(!ok("null"));
  assert.ok(!ok("2"));
});

test("rule 2: version is the number 2", () => {
  assert.ok(!ok(`{"outbox":[]}`));
  assert.ok(!ok(`{"version":"2","outbox":[]}`));
  assert.ok(!ok(`{"version":true,"outbox":[]}`));
  assert.ok(!ok(`{"version":1,"outbox":[]}`));
});

test("rule 3: outbox is an array", () => {
  assert.ok(!ok(`{"version":2}`));
  assert.ok(!ok(`{"version":2,"outbox":{}}`));
  assert.ok(!ok(`{"version":2,"outbox":null}`));
});

test("rule 4: entries", () => {
  assert.ok(!ok(st(["x"])));
  assert.ok(!ok(st([null])));
  assert.ok(!ok(st([{ to: "bob", text: "hi" }])));
  assert.ok(!ok(st([{ id: ID.toUpperCase(), to: "bob", text: "hi" }])));
  assert.ok(!ok(st([{ id: "abc", to: "bob", text: "hi" }])));
  assert.ok(!ok(st([{ id: ID, to: "", text: "hi" }])));
  assert.ok(!ok(st([{ id: ID, to: 5, text: "hi" }])));
  assert.ok(!ok(st([{ id: ID, to: "bob", text: "" }])));
  assert.ok(!ok(st([{ id: ID, to: "bob" }])));
  assert.ok(!ok(st([{ id: ID, to: "bob", text: "x".repeat(8193) }])));
  assert.ok(ok(st([{ id: ID, to: "bob", text: "x".repeat(8192) }])));
});

test("rule 5: unique ids", () => {
  assert.ok(!ok(st([{ id: ID, to: "a", text: "1" }, { id: ID, to: "b", text: "2" }])));
  assert.ok(ok(st([{ id: ID, to: "a", text: "1" }, { id: ID2, to: "b", text: "2" }])));
});

test("save and load round trip", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "msgtest-"));
  try {
    assert.deepEqual(loadOutbox(dir, "alice"), []);
    assert.ok(!fs.existsSync(path.join(dir, "alice")));
    const box = [{ id: ID, to: "bob", text: "a b" }];
    saveOutbox(dir, "alice", box);
    assert.deepEqual(loadOutbox(dir, "alice"), box);
    assert.ok(!fs.existsSync(path.join(dir, "alice", "state.json.tmp")));
    fs.writeFileSync(path.join(dir, "alice", "state.json"), "broken");
    assert.throws(() => loadOutbox(dir, "alice"));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
