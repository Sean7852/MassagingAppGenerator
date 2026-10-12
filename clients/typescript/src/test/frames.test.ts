// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { test } from "node:test";
import assert from "node:assert/strict";
import { parseServerFrame } from "../frames.js";

test("valid frames", () => {
  assert.deepEqual(parseServerFrame('{"type":"login_ok","name":"a","x":1}'), { type: "login_ok", name: "a" });
  assert.deepEqual(parseServerFrame('{"type":"ack","id":"i","seq":7.0}'), { type: "ack", id: "i", seq: 7 });
  assert.deepEqual(parseServerFrame('{"type":"deliver","seq":1,"id":"i","from":"f","text":"t"}'), {
    type: "deliver",
    seq: 1,
    id: "i",
    from: "f",
    text: "t",
  });
  assert.deepEqual(parseServerFrame('{"type":"error","code":"c","message":"m","ref":null}'), {
    type: "error",
    code: "c",
    message: "m",
  });
  assert.deepEqual(parseServerFrame('{"type":"error","code":"c","message":"m","ref":"r"}'), {
    type: "error",
    code: "c",
    message: "m",
    ref: "r",
  });
});

test("broken or unknown frames are ignored", () => {
  const bad = [
    "not json",
    "[]",
    "1",
    "null",
    '{"type":"nope"}',
    '{"name":"a"}',
    '{"type":"login_ok"}',
    '{"type":"ack","id":"i","seq":"7"}',
    '{"type":"ack","id":"i","seq":0}',
    '{"type":"ack","id":"i","seq":-1}',
    '{"type":"ack","id":"i","seq":7.5}',
    '{"type":"ack","id":"i","seq":9007199254740992}',
    '{"type":"ack","seq":1}',
    '{"type":"deliver","seq":1,"id":"i","from":2,"text":"t"}',
    '{"type":"deliver","seq":1,"id":"i","from":"f"}',
    '{"type":"error","code":"c","message":"m","ref":5}',
    '{"type":"error","code":"c"}',
  ];
  for (const f of bad) assert.equal(parseServerFrame(f), null, f);
});
