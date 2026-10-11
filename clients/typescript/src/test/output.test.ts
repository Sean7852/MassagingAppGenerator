// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { test } from "node:test";
import assert from "node:assert/strict";
import { errorLine, escape, recvLine, sentLine } from "../output.js";

test("escape replaces only backslash, LF, CR and tab", () => {
  assert.equal(escape("plain text"), "plain text");
  assert.equal(escape("a\\b"), "a\\\\b");
  assert.equal(escape("a\nb"), "a\\nb");
  assert.equal(escape("a\rb"), "a\\rb");
  assert.equal(escape("a\tb"), "a\\tb");
  assert.equal(escape("a\\nb"), "a\\\\nb");
  assert.equal(escape("héllo 你好 👋"), "héllo 你好 👋");
  assert.equal(escape(" x "), " x ");
});

test("line formats", () => {
  assert.equal(sentLine("id1", 3, "bob"), "SENT id=id1 seq=3 to=bob");
  assert.equal(recvLine(4, "id2", "alice", "a\tb"), "RECV seq=4 id=id2 from=alice text=a\\tb");
  assert.equal(errorLine("c", "m\n"), "ERROR code=c message=m\\n");
  assert.equal(errorLine("c", "m", "r"), "ERROR code=c ref=r message=m");
});
