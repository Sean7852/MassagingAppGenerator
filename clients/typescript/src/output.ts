// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

declare global {
  interface String {
    toWellFormed(): string;
  }
}

export type OutEvent =
  | { kind: "LOGGED_IN"; name: string }
  | { kind: "QUEUED"; id: string; to: string; text: string }
  | { kind: "SENT"; id: string; seq: number; to: string }
  | { kind: "RECV"; seq: number; id: string; from: string; text: string }
  | { kind: "ERROR"; code: string; ref?: string; message: string }
  | { kind: "OFFLINE" }
  | { kind: "DISCONNECTED" }
  | { kind: "BYE" };

const ESCAPES: Record<string, string> = { "\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t" };

/** Escapes <text> and <message> per 30-cli.md § Escaping. */
export function escapeText(s: string): string {
  return s.toWellFormed().replace(/[\\\n\r\t]/g, (c) => ESCAPES[c]);
}

/** Formats one output line (without the trailing newline). */
export function formatLine(ev: OutEvent, machine: boolean): string {
  switch (ev.kind) {
    case "LOGGED_IN":
      return machine ? `LOGGED_IN name=${ev.name}` : `Logged in as ${ev.name}`;
    case "QUEUED":
      return machine ? `QUEUED id=${ev.id} to=${ev.to}` : `[queued] to ${ev.to}: ${escapeText(ev.text)}`;
    case "SENT":
      return machine ? `SENT id=${ev.id} seq=${ev.seq} to=${ev.to}` : `[sent]   to ${ev.to} (#${ev.seq})`;
    case "RECV":
      return machine
        ? `RECV seq=${ev.seq} id=${ev.id} from=${ev.from} text=${escapeText(ev.text)}`
        : `[${ev.from}] ${escapeText(ev.text)}`;
    case "ERROR":
      if (!machine) return `Error: ${escapeText(ev.message)}`;
      return ev.ref !== undefined
        ? `ERROR code=${ev.code} ref=${ev.ref} message=${escapeText(ev.message)}`
        : `ERROR code=${ev.code} message=${escapeText(ev.message)}`;
    case "OFFLINE":
      return machine ? "OFFLINE" : "You are offline. Messages will be queued.";
    case "DISCONNECTED":
      return machine ? "DISCONNECTED" : "Disconnected. Type /online to reconnect.";
    case "BYE":
      return machine ? "BYE" : "Bye.";
  }
}

/** The only function that writes to stdout. */
export function writeLine(line: string): void {
  process.stdout.write(line + "\n");
}
