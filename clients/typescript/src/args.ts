// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

export interface Args {
  server: string;
  dataDir: string;
  machine: boolean;
}

export const USAGE = "usage: node dist/main.js [--server <url>] [--data-dir <dir>] [--machine]";

/** Parses the arguments per 30-cli.md § Invocation. Returns an error string on bad input. */
export function parseArgv(argv: string[]): Args | { error: string } {
  let server: string | undefined;
  let dataDir: string | undefined;
  let machine = false;
  let machineSeen = false;

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--machine") {
      if (machineSeen) return { error: "--machine given more than once" };
      machineSeen = true;
      machine = true;
      continue;
    }
    let key: "--server" | "--data-dir" | undefined;
    let value: string | undefined;
    for (const k of ["--server", "--data-dir"] as const) {
      if (arg === k) {
        key = k;
        if (i + 1 >= argv.length) return { error: `${k} needs a value` };
        value = argv[++i];
      } else if (arg.startsWith(k + "=")) {
        key = k;
        value = arg.slice(k.length + 1);
      }
    }
    if (key === undefined || value === undefined) return { error: `unexpected argument: ${arg}` };
    if (value === "") return { error: `${key} needs a non-empty value` };
    if (key === "--server") {
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
    machine,
  };
}
