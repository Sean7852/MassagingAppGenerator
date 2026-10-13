// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

export type Command =
  | { kind: "empty" }
  | { kind: "online" }
  | { kind: "offline" }
  | { kind: "quit" }
  | { kind: "login"; name: string }
  | { kind: "send"; to: string; text: string }
  | { kind: "usage"; command: "login" | "send" | "online" | "offline" | "quit" }
  | { kind: "unknown" };

const KEYWORDS = ["login", "send", "online", "offline", "quit"] as const;

/** Classifies one input line (line ending already removed) per the table in 30-cli.md. */
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
      const text = rest.slice(sp + 1);
      if (text.length > 0) return { kind: "send", to: rest.slice(0, sp), text };
    }
  }

  for (const k of KEYWORDS) {
    if (line === "/" + k || line.startsWith("/" + k + " ")) return { kind: "usage", command: k };
  }
  return { kind: "unknown" };
}

/** Splits stdin text into lines ending at "\r\n", "\n" or a lone "\r" (30-cli.md § Input). */
export class LineSplitter {
  private buf = "";
  private pendingCR = false;

  constructor(private readonly onLine: (line: string) => void) {}

  push(chunk: string): void {
    let start = 0;
    for (let i = 0; i < chunk.length; i++) {
      const ch = chunk[i];
      if (this.pendingCR) {
        this.pendingCR = false;
        if (ch === "\n") {
          start = i + 1;
          continue;
        }
      }
      if (ch === "\r" || ch === "\n") {
        const line = this.buf + chunk.slice(start, i);
        this.buf = "";
        start = i + 1;
        if (ch === "\r") this.pendingCR = true;
        this.onLine(line);
      }
    }
    this.buf += chunk.slice(start);
  }

  end(): void {
    if (this.buf.length > 0) {
      const line = this.buf;
      this.buf = "";
      this.onLine(line);
    }
  }
}
