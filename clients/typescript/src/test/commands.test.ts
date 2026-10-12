// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { test } from "node:test";
import assert from "node:assert/strict";
import { LineSplitter, parseCommand } from "../commands.js";

const usage = (message: string) => ({ kind: "usage", message });

test("exact commands", () => {
  assert.deepEqual(parseCommand("/online"), { kind: "online" });
  assert.deepEqual(parseCommand("/offline"), { kind: "offline" });
  assert.deepEqual(parseCommand("/quit"), { kind: "quit" });
  assert.deepEqual(parseCommand(""), { kind: "empty" });
});

test("/login", () => {
  assert.deepEqual(parseCommand("/login alice"), { kind: "login", name: "alice" });
  assert.deepEqual(parseCommand("/login Alice"), { kind: "login", name: "Alice" });
  assert.deepEqual(parseCommand("/login"), usage("usage: /login <name>"));
  assert.deepEqual(parseCommand("/login "), usage("usage: /login <name>"));
  assert.deepEqual(parseCommand("/login alice bob"), usage("usage: /login <name>"));
  assert.deepEqual(parseCommand("/login alice "), usage("usage: /login <name>"));
});

test("/send", () => {
  assert.deepEqual(parseCommand("/send bob hi there"), { kind: "send", to: "bob", text: "hi there" });
  assert.deepEqual(parseCommand("/send bob  hi"), { kind: "send", to: "bob", text: " hi" });
  assert.deepEqual(parseCommand("/send bob a b"), { kind: "send", to: "bob", text: "a b" });
  assert.deepEqual(parseCommand("/send bob a\tb "), { kind: "send", to: "bob", text: "a\tb " });
  assert.deepEqual(parseCommand("/send bob"), usage("usage: /send <user> <text>"));
  assert.deepEqual(parseCommand("/send bob "), usage("usage: /send <user> <text>"));
  assert.deepEqual(parseCommand("/send  bob hi"), usage("usage: /send <user> <text>"));
  assert.deepEqual(parseCommand("/send"), usage("usage: /send <user> <text>"));
});

test("usage errors for the other commands", () => {
  assert.deepEqual(parseCommand("/online now"), usage("usage: /online"));
  assert.deepEqual(parseCommand("/online "), usage("usage: /online"));
  assert.deepEqual(parseCommand("/offline please"), usage("usage: /offline"));
  assert.deepEqual(parseCommand("/quit now"), usage("usage: /quit"));
});

test("unknown commands", () => {
  for (const line of ["hello", "/sendx bob hi", "/Online", " /online", "/loginalice", "/quit\t"]) {
    assert.deepEqual(parseCommand(line), { kind: "unknown" }, line);
  }
});

function split(chunks: string[], end = true): string[] {
  const lines: string[] = [];
  const s = new LineSplitter((l) => lines.push(l));
  for (const c of chunks) s.push(c);
  if (end) s.end();
  return lines;
}

test("line splitting", () => {
  assert.deepEqual(split(["a\nb\r\nc\rd"]), ["a", "b", "c", "d"]);
  assert.deepEqual(split(["a\r", "\nb\n"]), ["a", "b"]);
  assert.deepEqual(split(["a\r", "b\n"]), ["a", "b"]);
  assert.deepEqual(split(["a\r\rb"]), ["a", "", "b"]);
  assert.deepEqual(split(["x y z\n"]), ["x y z"]);
  assert.deepEqual(split(["last"]), ["last"]);
  assert.deepEqual(split(["last"], false), []);
  assert.deepEqual(split(["a\n\n"]), ["a", ""]);
});
