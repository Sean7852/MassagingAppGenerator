// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { test } from "node:test";
import assert from "node:assert/strict";
import { parseArgs } from "../args.js";

test("defaults", () => {
  assert.deepEqual(parseArgs([]), {
    ok: true,
    options: { server: "ws://127.0.0.1:8765", dataDir: ".msgdata", machine: false },
  });
});

test("all options, both value forms, any order", () => {
  assert.deepEqual(parseArgs(["--machine", "--data-dir", "d", "--server=ws://x:1"]), {
    ok: true,
    options: { server: "ws://x:1", dataDir: "d", machine: true },
  });
  assert.deepEqual(parseArgs(["--server", "ws://y", "--data-dir=a=b"]), {
    ok: true,
    options: { server: "ws://y", dataDir: "a=b", machine: false },
  });
});

test("errors", () => {
  const bad = [
    ["--unknown"],
    ["-h"],
    ["--help"],
    ["--serv", "ws://x"],
    ["--serv=ws://x"],
    ["--machine", "--machine"],
    ["--server", "a", "--server", "b"],
    ["--server=a", "--server=b"],
    ["--data-dir", "a", "--data-dir=b"],
    ["--server"],
    ["--data-dir"],
    ["--server="],
    ["--data-dir="],
    ["--server", ""],
    ["--data-dir", ""],
    ["positional"],
    ["--machine=yes"],
  ];
  for (const argv of bad) {
    assert.equal(parseArgs(argv).ok, false, JSON.stringify(argv));
  }
});
