// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { test } from "node:test";
import assert from "node:assert/strict";
import { escapeText, formatEvent } from "../output.js";

test("escaping", () => {
  assert.equal(escapeText("a\\b"), "a\\\\b");
  assert.equal(escapeText("a\nb\rc\td"), "a\\nb\\rc\\td");
  assert.equal(escapeText("a\\nb"), "a\\\\nb");
  assert.equal(escapeText("x\uD800y"), "x�y");
  assert.equal(escapeText("x\uDC00"), "x�");
  assert.equal(escapeText("👋"), "👋");
  assert.equal(escapeText("a b é"), "a b é");
});

test("machine lines", () => {
  const m = (e: Parameters<typeof formatEvent>[0]) => formatEvent(e, true);
  assert.equal(m({ kind: "LOGGED_IN", name: "alice" }), "LOGGED_IN name=alice");
  assert.equal(m({ kind: "QUEUED", id: "i", to: "bob", text: "t" }), "QUEUED id=i to=bob");
  assert.equal(m({ kind: "SENT", id: "i", seq: 3, to: "bob" }), "SENT id=i seq=3 to=bob");
  assert.equal(
    m({ kind: "RECV", seq: 2, id: "i", from: "bob", text: "a\tb\uD800" }),
    "RECV seq=2 id=i from=bob text=a\\tb�",
  );
  assert.equal(m({ kind: "ERROR", code: "c", message: "m\n" }), "ERROR code=c message=m\\n");
  assert.equal(m({ kind: "ERROR", code: "c", ref: "r", message: "m" }), "ERROR code=c ref=r message=m");
  assert.equal(m({ kind: "READ", id: "i", seq: 4, by: "bob" }), "READ id=i seq=4 by=bob");
  assert.equal(m({ kind: "OFFLINE" }), "OFFLINE");
  assert.equal(m({ kind: "DISCONNECTED" }), "DISCONNECTED");
  assert.equal(m({ kind: "BYE" }), "BYE");
});

test("friendly lines", () => {
  const f = (e: Parameters<typeof formatEvent>[0]) => formatEvent(e, false);
  assert.equal(f({ kind: "LOGGED_IN", name: "alice" }), "Logged in as alice");
  assert.equal(f({ kind: "QUEUED", id: "i", to: "bob", text: "a\tb" }), "[queued] to bob: a\\tb");
  assert.equal(f({ kind: "SENT", id: "i", seq: 3, to: "bob" }), "[sent]   to bob (#3)");
  assert.equal(f({ kind: "RECV", seq: 2, id: "i", from: "bob", text: "x\\y\uDFFF" }), "[bob] x\\\\y�");
  assert.equal(f({ kind: "ERROR", code: "c", ref: "r", message: "m\r" }), "Error: m\\r");
  assert.equal(f({ kind: "READ", id: "i", seq: 4, by: "bob" }), "[read]   by bob (#4)");
  assert.equal(f({ kind: "OFFLINE" }), "You are offline. Messages will be queued.");
  assert.equal(f({ kind: "DISCONNECTED" }), "Disconnected. Type /online to reconnect.");
  assert.equal(f({ kind: "BYE" }), "Bye.");
});
