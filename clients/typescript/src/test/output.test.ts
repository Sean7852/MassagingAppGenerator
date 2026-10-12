// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { test } from "node:test";
import assert from "node:assert/strict";
import { escapeText, formatLine } from "../output.js";

const ID = "0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11";

test("escaping", () => {
  assert.equal(escapeText("a\\b"), "a\\\\b");
  assert.equal(escapeText("a\nb\rc\td"), "a\\nb\\rc\\td");
  assert.equal(escapeText("a\\nb"), "a\\\\nb");
  assert.equal(escapeText("x\uD800y"), "x�y");
  assert.equal(escapeText("x\uDC00"), "x�");
  assert.equal(escapeText("👋 é  "), "👋 é  ");
});

test("machine lines", () => {
  const m = true;
  assert.equal(formatLine({ kind: "LOGGED_IN", name: "alice" }, m), "LOGGED_IN name=alice");
  assert.equal(formatLine({ kind: "QUEUED", id: ID, to: "bob", text: "x" }, m), `QUEUED id=${ID} to=bob`);
  assert.equal(formatLine({ kind: "SENT", id: ID, seq: 3, to: "bob" }, m), `SENT id=${ID} seq=3 to=bob`);
  assert.equal(
    formatLine({ kind: "RECV", seq: 2, id: ID, from: "bob", text: "a\tb\uD800" }, m),
    `RECV seq=2 id=${ID} from=bob text=a\\tb�`,
  );
  assert.equal(formatLine({ kind: "ERROR", code: "c", message: "m\n" }, m), "ERROR code=c message=m\\n");
  assert.equal(formatLine({ kind: "ERROR", code: "c", ref: ID, message: "m" }, m), `ERROR code=c ref=${ID} message=m`);
  assert.equal(formatLine({ kind: "OFFLINE" }, m), "OFFLINE");
  assert.equal(formatLine({ kind: "DISCONNECTED" }, m), "DISCONNECTED");
  assert.equal(formatLine({ kind: "BYE" }, m), "BYE");
});

test("friendly lines", () => {
  const f = false;
  assert.equal(formatLine({ kind: "LOGGED_IN", name: "alice" }, f), "Logged in as alice");
  assert.equal(formatLine({ kind: "QUEUED", id: ID, to: "bob", text: "a\tb" }, f), "[queued] to bob: a\\tb");
  assert.equal(formatLine({ kind: "SENT", id: ID, seq: 3, to: "bob" }, f), "[sent]   to bob (#3)");
  assert.equal(formatLine({ kind: "RECV", seq: 2, id: ID, from: "bob", text: "x\\\uDBFF" }, f), "[bob] x\\\\�");
  assert.equal(formatLine({ kind: "ERROR", code: "c", ref: ID, message: "bad\r" }, f), "Error: bad\\r");
  assert.equal(formatLine({ kind: "OFFLINE" }, f), "You are offline. Messages will be queued.");
  assert.equal(formatLine({ kind: "DISCONNECTED" }, f), "Disconnected. Type /online to reconnect.");
  assert.equal(formatLine({ kind: "BYE" }, f), "Bye.");
});
