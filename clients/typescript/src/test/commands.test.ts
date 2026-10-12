// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { test } from "node:test";
import assert from "node:assert/strict";
import { parseCommand } from "../commands.js";

const usage = (message: string) => ({ kind: "usage", message });
const LOGIN = usage("usage: /login <name>");
const SEND = usage("usage: /send <user> <text>");

test("exact commands", () => {
  assert.deepEqual(parseCommand("/online"), { kind: "online" });
  assert.deepEqual(parseCommand("/offline"), { kind: "offline" });
  assert.deepEqual(parseCommand("/quit"), { kind: "quit" });
  assert.deepEqual(parseCommand(""), { kind: "empty" });
});

test("/login", () => {
  assert.deepEqual(parseCommand("/login alice"), { kind: "login", name: "alice" });
  assert.deepEqual(parseCommand("/login Alice"), { kind: "login", name: "Alice" });
  assert.deepEqual(parseCommand("/login"), LOGIN);
  assert.deepEqual(parseCommand("/login "), LOGIN);
  assert.deepEqual(parseCommand("/login alice bob"), LOGIN);
  assert.deepEqual(parseCommand("/login  alice"), LOGIN);
  assert.deepEqual(parseCommand("/login alice "), LOGIN);
});

test("/send", () => {
  assert.deepEqual(parseCommand("/send bob hi there"), { kind: "send", to: "bob", text: "hi there" });
  assert.deepEqual(parseCommand("/send bob  hi"), { kind: "send", to: "bob", text: " hi" });
  assert.deepEqual(parseCommand("/send bob a\tb "), { kind: "send", to: "bob", text: "a\tb " });
  assert.deepEqual(parseCommand("/send bob a b"), { kind: "send", to: "bob", text: "a b" });
  assert.deepEqual(parseCommand("/send bob  "), { kind: "send", to: "bob", text: " " });
  assert.deepEqual(parseCommand("/send bob"), SEND);
  assert.deepEqual(parseCommand("/send bob "), SEND);
  assert.deepEqual(parseCommand("/send  bob hi"), SEND);
  assert.deepEqual(parseCommand("/send"), SEND);
  assert.deepEqual(parseCommand("/send "), SEND);
});

test("usage errors for other commands", () => {
  assert.deepEqual(parseCommand("/online now"), usage("usage: /online"));
  assert.deepEqual(parseCommand("/online "), usage("usage: /online"));
  assert.deepEqual(parseCommand("/offline please"), usage("usage: /offline"));
  assert.deepEqual(parseCommand("/quit now"), usage("usage: /quit"));
});

test("unknown commands", () => {
  for (const line of ["hello", "/sendx bob hi", "/loginx", "/Online", " /quit", "/quit\t", "/"]) {
    assert.deepEqual(parseCommand(line), { kind: "unknown" }, line);
  }
});
