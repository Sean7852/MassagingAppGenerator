// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { test } from "node:test";
import assert from "node:assert/strict";
import { Client, type ClientEvent, type Conn } from "../client.js";

class FakeConn implements Conn {
  sent: unknown[] = [];
  closed = false;
  send(data: string): void {
    this.sent.push(JSON.parse(data));
  }
  close(): void {
    this.closed = true;
  }
}

function setup(failConnect = false) {
  const out: string[] = [];
  const conns: FakeConn[] = [];
  let n = 0;
  const client = new Client(
    "ws://x",
    () => {
      if (failConnect) throw new Error("bad url");
      const c = new FakeConn();
      conns.push(c);
      return c;
    },
    (_e: ClientEvent) => {},
    (line) => out.push(line),
    () => `id${++n}`,
  );
  const msg = (conn: Conn, frame: object) =>
    client.handle({ kind: "message", conn, data: JSON.stringify(frame) });
  const online = (name = "alice") => {
    client.handle({ kind: "line", line: `/login ${name}` });
    const c = conns[conns.length - 1];
    client.handle({ kind: "open", conn: c });
    msg(c, { type: "login_ok", name });
    return c;
  };
  return { client, out, conns, msg, online };
}

test("connect failure prints connect_failed and returns to idle", () => {
  const { client, out } = setup(true);
  client.handle({ kind: "line", line: "/login alice" });
  assert.deepEqual(out, ["ERROR code=connect_failed message=cannot connect to ws://x"]);
});

test("close before open is connect_failed", () => {
  const { client, out, conns } = setup();
  client.handle({ kind: "line", line: "/login alice" });
  client.handle({ kind: "close", conn: conns[0] });
  assert.deepEqual(out, ["ERROR code=connect_failed message=cannot connect to ws://x"]);
});

test("sends one at a time and reports not_sent on loss", () => {
  const { client, out, msg, online } = setup();
  const c = online();
  assert.deepEqual(c.sent, [{ type: "login", name: "alice" }]);
  client.handle({ kind: "line", line: "/send bob one" });
  client.handle({ kind: "line", line: "/send bob two" });
  assert.equal(c.sent.length, 2);
  msg(c, { type: "ack", id: "id1", seq: 7 });
  assert.equal(c.sent.length, 3);
  client.handle({ kind: "close", conn: c });
  assert.deepEqual(out, [
    "LOGGED_IN name=alice",
    "SENT id=id1 seq=7 to=bob",
    "ERROR code=not_sent ref=id2 message=connection lost before the server acknowledged the message",
    "DISCONNECTED",
  ]);
});

test("deliver is shown once and always acked", () => {
  const { out, msg, online } = setup();
  const c = online();
  const d = { type: "deliver", seq: 1, id: "m", from: "bob", to: "alice", text: "hi" };
  msg(c, d);
  msg(c, { ...d, seq: 2 });
  assert.deepEqual(out, ["LOGGED_IN name=alice", "RECV seq=1 id=m from=bob text=hi"]);
  assert.deepEqual(c.sent.slice(1), [
    { type: "deliver_ack", seq: 1 },
    { type: "deliver_ack", seq: 2 },
  ]);
});

test("error before login_ok closes without DISCONNECTED", () => {
  const { client, out, conns, msg } = setup();
  client.handle({ kind: "line", line: "/login Alice" });
  client.handle({ kind: "open", conn: conns[0] });
  msg(conns[0], { type: "error", code: "invalid_name", message: "bad" });
  client.handle({ kind: "close", conn: conns[0] });
  assert.equal(conns[0].closed, true);
  assert.deepEqual(out, ["ERROR code=invalid_name message=bad"]);
});

test("quit prints BYE and nothing after", () => {
  const { client, out, online } = setup();
  const c = online();
  client.handle({ kind: "line", line: "/send bob x" });
  client.handle({ kind: "eof" });
  client.handle({ kind: "close", conn: c });
  assert.deepEqual(out, ["LOGGED_IN name=alice", "BYE"]);
  assert.equal(c.closed, true);
});
