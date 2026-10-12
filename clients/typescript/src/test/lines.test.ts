// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { test } from "node:test";
import assert from "node:assert/strict";
import { LineSplitter } from "../lines.js";

function split(chunks: string[]): string[] {
  const s = new LineSplitter();
  const out: string[] = [];
  for (const c of chunks) out.push(...s.push(c));
  out.push(...s.end());
  return out;
}

test("line endings", () => {
  assert.deepEqual(split(["a\nb\r\nc\rd"]), ["a", "b", "c", "d"]);
  assert.deepEqual(split(["a\r", "\nb"]), ["a", "b"]);
  assert.deepEqual(split(["a\r", "b\n"]), ["a", "b"]);
  assert.deepEqual(split(["\n\n"]), ["", ""]);
  assert.deepEqual(split(["a\r\r\nb"]), ["a", "", "b"]);
  assert.deepEqual(split(["/send bob first\r/send bob second\n"]), ["/send bob first", "/send bob second"]);
});

test("U+2028 and U+2029 do not end a line", () => {
  assert.deepEqual(split(["/send bob a b c\n"]), ["/send bob a b c"]);
});

test("partial chunks and a last line without ending", () => {
  assert.deepEqual(split(["/se", "nd bob ", "hi"]), ["/send bob hi"]);
  assert.deepEqual(split([]), []);
  assert.deepEqual(split(["x\t \n"]), ["x\t "]);
});
