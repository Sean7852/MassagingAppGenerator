// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

export type Command =
  | { kind: "online" }
  | { kind: "offline" }
  | { kind: "quit" }
  | { kind: "login"; name: string }
  | { kind: "send"; to: string; text: string }
  | { kind: "usage"; message: string }
  | { kind: "unknown" }
  | { kind: "empty" };

const USAGES: Record<string, string> = {
  "/login": "usage: /login <name>",
  "/send": "usage: /send <user> <text>",
  "/online": "usage: /online",
  "/offline": "usage: /offline",
  "/quit": "usage: /quit",
};

/** Parses one input line (line ending already removed) per the table in 30-cli.md. */
export function parseCommand(line: string): Command {
  if (line === "") return { kind: "empty" };
  if (line === "/online") return { kind: "online" };
  if (line === "/offline") return { kind: "offline" };
  if (line === "/quit") return { kind: "quit" };

  if (line.startsWith("/login ")) {
    const name = line.slice("/login ".length);
    if (name.length > 0 && !name.includes(" ")) return { kind: "login", name };
  }

  if (line.startsWith("/send ")) {
    const rest = line.slice("/send ".length);
    const sp = rest.indexOf(" ");
    if (sp > 0) {
      const to = rest.slice(0, sp);
      const text = rest.slice(sp + 1);
      if (text.length > 0) return { kind: "send", to, text };
    }
  }

  for (const word of Object.keys(USAGES)) {
    if (line === word || line.startsWith(word + " ")) {
      return { kind: "usage", message: USAGES[word] };
    }
  }
  return { kind: "unknown" };
}

/**
 * Splits a stream of text chunks into lines ending at "\r\n", "\n" or a lone "\r".
 * A "\r" at the end of a chunk waits for the next chunk.
 */
export class LineSplitter {
  private buf = "";
  private pendingCR = false;

  constructor(private readonly onLine: (line: string) => void) {}

  push(chunk: string): void {
    for (const ch of chunk) {
      if (this.pendingCR) {
        this.pendingCR = false;
        if (ch === "\n") continue; // "\r\n": the line was already emitted at "\r"
      }
      if (ch === "\r") {
        this.emit();
        this.pendingCR = true;
      } else if (ch === "\n") {
        this.emit();
      } else {
        this.buf += ch;
      }
    }
  }

  end(): void {
    this.pendingCR = false;
    if (this.buf.length > 0) this.emit();
  }

  private emit(): void {
    const line = this.buf;
    this.buf = "";
    this.onLine(line);
  }
}
