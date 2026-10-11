// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { test } from "node:test";
import assert from "node:assert/strict";
import { parseLine } from "../commands.js";

const LOGIN_USAGE = { kind: "usage", message: "usage: /login <name>" };
const SEND_USAGE = { kind: "usage", message: "usage: /send <user> <text>" };
const QUIT_USAGE = { kind: "usage", message: "usage: /quit" };

test("empty line is ignored", () => {
  assert.deepEqual(parseLine(""), { kind: "empty" });
});

test("/login <name>", () => {
  assert.deepEqual(parseLine("/login alice"), { kind: "login", name: "alice" });
  assert.deepEqual(parseLine("/login Alice!"), { kind: "login", name: "Alice!" });
  assert.deepEqual(parseLine("/login a\tb"), { kind: "login", name: "a\tb" });
});

test("/send <to> <text> keeps text exactly", () => {
  assert.deepEqual(parseLine("/send bob hi"), { kind: "send", to: "bob", text: "hi" });
  assert.deepEqual(parseLine("/send bob  hi "), { kind: "send", to: "bob", text: " hi " });
  assert.deepEqual(parseLine("/send bob a b  c"), { kind: "send", to: "bob", text: "a b  c" });
  assert.deepEqual(parseLine("/send bob a\\nb"), { kind: "send", to: "bob", text: "a\\nb" });
  assert.deepEqual(parseLine("/send bob x y"), { kind: "send", to: "bob", text: "x y" });
});

test("/quit", () => {
  assert.deepEqual(parseLine("/quit"), { kind: "quit" });
});

test("usage errors", () => {
  assert.deepEqual(parseLine("/login"), LOGIN_USAGE);
  assert.deepEqual(parseLine("/login "), LOGIN_USAGE);
  assert.deepEqual(parseLine("/login alice extra"), LOGIN_USAGE);
  assert.deepEqual(parseLine("/login  alice"), LOGIN_USAGE);
  assert.deepEqual(parseLine("/send"), SEND_USAGE);
  assert.deepEqual(parseLine("/send bob"), SEND_USAGE);
  assert.deepEqual(parseLine("/send bob "), SEND_USAGE);
  assert.deepEqual(parseLine("/send  bob hi"), SEND_USAGE);
  assert.deepEqual(parseLine("/quit now"), QUIT_USAGE);
  assert.deepEqual(parseLine("/quit "), QUIT_USAGE);
});

test("unknown commands", () => {
  for (const line of ["hello", "/sendx bob hi", "/loginalice", "/quitx", "/LOGIN alice", " /quit"]) {
    assert.deepEqual(parseLine(line), { kind: "unknown" }, line);
  }
});
