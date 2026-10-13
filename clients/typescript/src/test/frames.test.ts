// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { test } from "node:test";
import assert from "node:assert/strict";
import { parseFrame } from "../frames.js";

test("valid frames", () => {
  assert.deepEqual(parseFrame('{"type":"login_ok","name":"a","x":1}'), { type: "login_ok", name: "a" });
  assert.deepEqual(parseFrame('{"type":"ack","id":"i","seq":7.0}'), { type: "ack", id: "i", seq: 7 });
  assert.deepEqual(parseFrame('{"type":"deliver","seq":1,"id":"i","from":"a","text":"t"}'), {
    type: "deliver",
    seq: 1,
    id: "i",
    from: "a",
    text: "t",
  });
  assert.deepEqual(parseFrame('{"type":"error","code":"c","message":"m","ref":null}'), {
    type: "error",
    code: "c",
    message: "m",
  });
  assert.deepEqual(parseFrame('{"type":"error","code":"c","message":"m","ref":"r"}'), {
    type: "error",
    code: "c",
    message: "m",
    ref: "r",
  });
  assert.deepEqual(parseFrame('{"type":"receipt","seq":4,"msg_seq":3,"msg_id":"i","by":"b"}'), {
    type: "receipt",
    seq: 4,
    msg_seq: 3,
    msg_id: "i",
    by: "b",
  });
});

test("broken or unknown frames are null", () => {
  for (const raw of [
    "nope",
    "[]",
    "null",
    '{"type":"what"}',
    '{"name":"a"}',
    '{"type":"login_ok"}',
    '{"type":"ack","id":"i","seq":"7"}',
    '{"type":"ack","id":"i","seq":0}',
    '{"type":"ack","id":"i","seq":-1}',
    '{"type":"ack","id":"i","seq":7.5}',
    '{"type":"ack","id":"i","seq":9007199254740992}',
    '{"type":"ack","seq":1}',
    '{"type":"deliver","seq":1,"id":"i","from":"a"}',
    '{"type":"deliver","seq":1,"id":5,"from":"a","text":"t"}',
    '{"type":"error","code":"c","message":"m","ref":5}',
    '{"type":"error","code":"c"}',
    '{"type":"receipt","seq":4,"msg_seq":"3","msg_id":"i","by":"b"}',
    '{"type":"receipt","seq":4,"msg_seq":3,"by":"b"}',
  ]) {
    assert.equal(parseFrame(raw), null, raw);
  }
});
