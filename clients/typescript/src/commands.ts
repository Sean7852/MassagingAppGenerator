// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

export type Command =
  | { kind: "empty" }
  | { kind: "online" }
  | { kind: "offline" }
  | { kind: "quit" }
  | { kind: "login"; name: string }
  | { kind: "send"; to: string; text: string }
  | { kind: "usage"; message: string }
  | { kind: "unknown" };

const USAGES: Record<string, string> = {
  "/login": "usage: /login <name>",
  "/send": "usage: /send <user> <text>",
  "/online": "usage: /online",
  "/offline": "usage: /offline",
  "/quit": "usage: /quit",
};

const LOGIN_RE = /^\/login ([^ ]+)$/;
const SEND_RE = /^\/send ([^ ]+) ([\s\S]+)$/;

/** Parses one input line (line ending already removed) per 30-cli.md § Commands. */
export function parseCommand(line: string): Command {
  if (line === "") return { kind: "empty" };
  if (line === "/online") return { kind: "online" };
  if (line === "/offline") return { kind: "offline" };
  if (line === "/quit") return { kind: "quit" };
  const login = LOGIN_RE.exec(line);
  if (login) return { kind: "login", name: login[1] };
  const send = SEND_RE.exec(line);
  if (send) return { kind: "send", to: send[1], text: send[2] };
  for (const cmd of Object.keys(USAGES)) {
    if (line === cmd || line.startsWith(cmd + " ")) return { kind: "usage", message: USAGES[cmd] };
  }
  return { kind: "unknown" };
}
