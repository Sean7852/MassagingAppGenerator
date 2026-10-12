// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

export type Command =
  | { kind: "empty" }
  | { kind: "login"; name: string }
  | { kind: "send"; to: string; text: string }
  | { kind: "quit" }
  | { kind: "usage"; message: string }
  | { kind: "unknown" };

const LOGIN_RE = /^\/login ([^ ]+)$/s;
const SEND_RE = /^\/send ([^ ]+) (.+)$/s;

function startsCommand(line: string, word: string): boolean {
  return line === word || line.startsWith(word + " ");
}

/** Parses one input line (line ending already removed) per the table in 30-cli.md. */
export function parseLine(line: string): Command {
  if (line === "") return { kind: "empty" };
  let m = LOGIN_RE.exec(line);
  if (m) return { kind: "login", name: m[1] };
  m = SEND_RE.exec(line);
  if (m) return { kind: "send", to: m[1], text: m[2] };
  if (line === "/quit") return { kind: "quit" };
  if (startsCommand(line, "/login")) return { kind: "usage", message: "usage: /login <name>" };
  if (startsCommand(line, "/send")) return { kind: "usage", message: "usage: /send <user> <text>" };
  if (startsCommand(line, "/quit")) return { kind: "usage", message: "usage: /quit" };
  return { kind: "unknown" };
}
