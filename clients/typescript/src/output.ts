// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

/** Escapes a text or server message for output (30-cli.md § Escaping). */
export function escapeText(s: string): string {
  const w = s.toWellFormed();
  let out = "";
  for (const ch of w) {
    if (ch === "\\") out += "\\\\";
    else if (ch === "\n") out += "\\n";
    else if (ch === "\r") out += "\\r";
    else if (ch === "\t") out += "\\t";
    else out += ch;
  }
  return out;
}

export type Event =
  | { kind: "LOGGED_IN"; name: string }
  | { kind: "QUEUED"; id: string; to: string; text: string }
  | { kind: "SENT"; id: string; seq: number; to: string }
  | { kind: "RECV"; seq: number; id: string; from: string; text: string }
  | { kind: "ERROR"; code: string; ref?: string; message: string }
  | { kind: "READ"; id: string; seq: number; by: string }
  | { kind: "OFFLINE" }
  | { kind: "DISCONNECTED" }
  | { kind: "BYE" };

/** Formats one event as an output line (without the line ending). */
export function formatEvent(e: Event, machine: boolean): string {
  switch (e.kind) {
    case "LOGGED_IN":
      return machine ? `LOGGED_IN name=${e.name}` : `Logged in as ${e.name}`;
    case "QUEUED":
      return machine ? `QUEUED id=${e.id} to=${e.to}` : `[queued] to ${e.to}: ${escapeText(e.text)}`;
    case "SENT":
      return machine ? `SENT id=${e.id} seq=${e.seq} to=${e.to}` : `[sent]   to ${e.to} (#${e.seq})`;
    case "RECV":
      return machine
        ? `RECV seq=${e.seq} id=${e.id} from=${e.from} text=${escapeText(e.text)}`
        : `[${e.from}] ${escapeText(e.text)}`;
    case "ERROR":
      if (!machine) return `Error: ${escapeText(e.message)}`;
      return e.ref !== undefined
        ? `ERROR code=${e.code} ref=${e.ref} message=${escapeText(e.message)}`
        : `ERROR code=${e.code} message=${escapeText(e.message)}`;
    case "READ":
      return machine ? `READ id=${e.id} seq=${e.seq} by=${e.by}` : `[read]   by ${e.by} (#${e.seq})`;
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
