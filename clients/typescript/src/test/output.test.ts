// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { test } from "node:test";
import assert from "node:assert/strict";
import { escapeText, formatEvent, type Event } from "../output.js";

test("escaping", () => {
  assert.equal(escapeText("a\\b"), "a\\\\b");
  assert.equal(escapeText("a\nb\rc\td"), "a\\nb\\rc\\td");
  assert.equal(escapeText("x\uD800y"), "x�y");
  assert.equal(escapeText("x\uDC00"), "x�");
  assert.equal(escapeText("👋 é  "), "👋 é  ");
  assert.equal(escapeText("a\\nb"), "a\\\\nb");
});

const id = "0b6c1f4e-2f0a-4c1e-9a53-0f7e1f3d2b11";

test("machine and friendly lines", () => {
  const cases: [Event, string, string][] = [
    [{ kind: "LOGGED_IN", name: "alice" }, "LOGGED_IN name=alice", "Logged in as alice"],
    [{ kind: "QUEUED", id, to: "bob", text: "a\tb" }, `QUEUED id=${id} to=bob`, "[queued] to bob: a\\tb"],
    [{ kind: "SENT", id, seq: 3, to: "bob" }, `SENT id=${id} seq=3 to=bob`, "[sent]   to bob (#3)"],
    [
      { kind: "RECV", seq: 2, id, from: "bob", text: "hi\n\uD800" },
      `RECV seq=2 id=${id} from=bob text=hi\\n�`,
      "[bob] hi\\n�",
    ],
    [{ kind: "ERROR", code: "c", message: "m\\" }, "ERROR code=c message=m\\\\", "Error: m\\\\"],
    [{ kind: "ERROR", code: "c", ref: id, message: "m" }, `ERROR code=c ref=${id} message=m`, "Error: m"],
    [{ kind: "READ", msgId: id, msgSeq: 3, by: "bob" }, `READ id=${id} seq=3 by=bob`, "[read]   by bob (#3)"],
    [{ kind: "OFFLINE" }, "OFFLINE", "You are offline. Messages will be queued."],
    [{ kind: "DISCONNECTED" }, "DISCONNECTED", "Disconnected. Type /online to reconnect."],
    [{ kind: "BYE" }, "BYE", "Bye."],
  ];
  for (const [ev, machine, friendly] of cases) {
    assert.equal(formatEvent(ev, true), machine);
    assert.equal(formatEvent(ev, false), friendly);
  }
});
