// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { test } from "node:test";
import assert from "node:assert/strict";
import { parseArgs } from "../args.js";

test("defaults", () => {
  assert.deepEqual(parseArgs([]), { server: "ws://127.0.0.1:8765", dataDir: ".msgdata", machine: false });
});

test("all options, both value forms, any order", () => {
  assert.deepEqual(parseArgs(["--machine", "--server", "ws://h:1", "--data-dir=d"]), {
    server: "ws://h:1",
    dataDir: "d",
    machine: true,
  });
  assert.deepEqual(parseArgs(["--data-dir", "x", "--server=ws://a=b"]), {
    server: "ws://a=b",
    dataDir: "x",
    machine: false,
  });
});

test("errors", () => {
  const bad: string[][] = [
    ["--unknown"],
    ["-h"],
    ["--help"],
    ["--serv", "ws://x"],
    ["--machine", "--machine"],
    ["--server", "a", "--server", "b"],
    ["--server=a", "--server=b"],
    ["--data-dir", "a", "--data-dir=b"],
    ["--server"],
    ["--data-dir"],
    ["--server="],
    ["--data-dir="],
    ["--server", ""],
    ["positional"],
    ["--machine=1"],
  ];
  for (const argv of bad) {
    assert.ok("error" in parseArgs(argv), JSON.stringify(argv));
  }
});
