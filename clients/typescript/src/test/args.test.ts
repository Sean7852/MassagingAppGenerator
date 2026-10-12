// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { test } from "node:test";
import assert from "node:assert/strict";
import { parseArgv } from "../args.js";

test("defaults", () => {
  assert.deepEqual(parseArgv([]), { server: "ws://127.0.0.1:8765", dataDir: ".msgdata", machine: false });
});

test("values as next argument or after =", () => {
  assert.deepEqual(parseArgv(["--machine", "--server", "ws://h:1", "--data-dir=d"]), {
    server: "ws://h:1",
    dataDir: "d",
    machine: true,
  });
  assert.deepEqual(parseArgv(["--data-dir", "x y", "--server=ws://a=b"]), {
    server: "ws://a=b",
    dataDir: "x y",
    machine: false,
  });
});

test("errors", () => {
  const bad = [
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
    ["--data-dir", ""],
    ["positional"],
    ["--machine=1"],
    ["-"],
    ["--"],
  ];
  for (const argv of bad) assert.ok("error" in parseArgv(argv), JSON.stringify(argv));
});
