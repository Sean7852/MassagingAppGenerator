// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

const ESCAPES: Record<string, string> = {
  "\\": "\\\\",
  "\n": "\\n",
  "\r": "\\r",
  "\t": "\\t",
};

/** Escapes <text> and <message> values as 30-cli.md says. */
export function escape(value: string): string {
  return value.replace(/[\\\n\r\t]/g, (c) => ESCAPES[c]);
}

export function loggedInLine(name: string): string {
  return `LOGGED_IN name=${name}`;
}

export function sentLine(id: string, seq: number, to: string): string {
  return `SENT id=${id} seq=${seq} to=${to}`;
}

export function recvLine(seq: number, id: string, from: string, text: string): string {
  return `RECV seq=${seq} id=${id} from=${from} text=${escape(text)}`;
}

export function errorLine(code: string, message: string, ref?: string): string {
  if (ref !== undefined) return `ERROR code=${code} ref=${ref} message=${escape(message)}`;
  return `ERROR code=${code} message=${escape(message)}`;
}

/** The only function that writes to stdout. */
export function writeLine(line: string): void {
  process.stdout.write(line + "\n");
}
