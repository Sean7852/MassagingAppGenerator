// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

export interface Options {
  server: string;
  dataDir: string;
  machine: boolean;
}

export const USAGE = "usage: node dist/main.js [--server <url>] [--data-dir <dir>] [--machine]";

/** Parses the command-line arguments (30-cli.md § Invocation). Returns an error string on bad input. */
export function parseArgs(argv: string[]): Options | { error: string } {
  let server: string | undefined;
  let dataDir: string | undefined;
  let machine: boolean | undefined;

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--machine") {
      if (machine !== undefined) return { error: "--machine given more than once" };
      machine = true;
      continue;
    }
    let key: "server" | "data-dir" | undefined;
    let value: string | undefined;
    for (const k of ["server", "data-dir"] as const) {
      const opt = "--" + k;
      if (arg === opt) {
        key = k;
        value = i + 1 < argv.length ? argv[++i] : undefined;
        break;
      }
      if (arg.startsWith(opt + "=")) {
        key = k;
        value = arg.slice(opt.length + 1);
        break;
      }
    }
    if (key === undefined) return { error: `unknown argument: ${arg}` };
    if (value === undefined || value === "") return { error: `--${key} needs a non-empty value` };
    if (key === "server") {
      if (server !== undefined) return { error: "--server given more than once" };
      server = value;
    } else {
      if (dataDir !== undefined) return { error: "--data-dir given more than once" };
      dataDir = value;
    }
  }

  return {
    server: server ?? "ws://127.0.0.1:8765",
    dataDir: dataDir ?? ".msgdata",
    machine: machine ?? false,
  };
}
