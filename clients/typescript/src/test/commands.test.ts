// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { test } from "node:test";
import assert from "node:assert/strict";
import { parseCommand, LineSplitter } from "../commands.js";

test("exact commands", () => {
  assert.deepEqual(parseCommand("/online"), { kind: "online" });
  assert.deepEqual(parseCommand("/offline"), { kind: "offline" });
  assert.deepEqual(parseCommand("/quit"), { kind: "quit" });
  assert.deepEqual(parseCommand(""), { kind: "empty" });
});

test("login", () => {
  assert.deepEqual(parseCommand("/login alice"), { kind: "login", name: "alice" });
  assert.deepEqual(parseCommand("/login Alice"), { kind: "login", name: "Alice" });
  assert.deepEqual(parseCommand("/login"), { kind: "usage", command: "login" });
  assert.deepEqual(parseCommand("/login "), { kind: "usage", command: "login" });
  assert.deepEqual(parseCommand("/login alice bob"), { kind: "usage", command: "login" });
  assert.deepEqual(parseCommand("/login  alice"), { kind: "usage", command: "login" });
});

test("send examples from 30-cli.md", () => {
  assert.deepEqual(parseCommand("/send bob hi there"), { kind: "send", to: "bob", text: "hi there" });
  assert.deepEqual(parseCommand("/send bob  hi"), { kind: "send", to: "bob", text: " hi" });
  assert.deepEqual(parseCommand("/send bob"), { kind: "usage", command: "send" });
  assert.deepEqual(parseCommand("/send bob "), { kind: "usage", command: "send" });
  assert.deepEqual(parseCommand("/send  bob hi"), { kind: "usage", command: "send" });
  assert.deepEqual(parseCommand("/send"), { kind: "usage", command: "send" });
  assert.deepEqual(parseCommand("/sendx bob hi"), { kind: "unknown" });
});

test("send text keeps every character", () => {
  assert.deepEqual(parseCommand("/send bob a b"), { kind: "send", to: "bob", text: "a b" });
  assert.deepEqual(parseCommand("/send bob a\tb "), { kind: "send", to: "bob", text: "a\tb " });
  assert.deepEqual(parseCommand("/send b\tob x"), { kind: "send", to: "b\tob", text: "x" });
});

test("usage errors for keywords followed by a space", () => {
  assert.deepEqual(parseCommand("/online now"), { kind: "usage", command: "online" });
  assert.deepEqual(parseCommand("/online "), { kind: "usage", command: "online" });
  assert.deepEqual(parseCommand("/offline please"), { kind: "usage", command: "offline" });
  assert.deepEqual(parseCommand("/quit now"), { kind: "usage", command: "quit" });
});

test("unknown commands", () => {
  assert.deepEqual(parseCommand("hello"), { kind: "unknown" });
  assert.deepEqual(parseCommand("/onlinex"), { kind: "unknown" });
  assert.deepEqual(parseCommand(" /online"), { kind: "unknown" });
  assert.deepEqual(parseCommand("/Online"), { kind: "unknown" });
});

function split(chunks: string[], end = true): string[] {
  const lines: string[] = [];
  const s = new LineSplitter((l) => lines.push(l));
  for (const c of chunks) s.push(c);
  if (end) s.end();
  return lines;
}

test("line splitter endings", () => {
  assert.deepEqual(split(["a\nb\r\nc\rd"]), ["a", "b", "c", "d"]);
  assert.deepEqual(split(["a\r", "\nb\n"]), ["a", "b"]);
  assert.deepEqual(split(["a\r", "b\n"]), ["a", "b"]);
  assert.deepEqual(split(["a\r\r\n"]), ["a", ""]);
  assert.deepEqual(split(["a\n\nb"]), ["a", "", "b"]);
  assert.deepEqual(split(["x y z\n"]), ["x y z"]);
  assert.deepEqual(split(["last"], false), []);
  assert.deepEqual(split(["last"]), ["last"]);
});
