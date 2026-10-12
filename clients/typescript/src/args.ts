// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

export interface Options {
  server: string;
  dataDir: string;
  machine: boolean;
}

export type ArgsResult = { ok: true; options: Options } | { ok: false; error: string };

export const USAGE = "usage: main [--server <url>] [--data-dir <dir>] [--machine]";

/** Parses the command-line arguments exactly as 30-cli.md § Invocation says. */
export function parseArgs(argv: readonly string[]): ArgsResult {
  let server: string | undefined;
  let dataDir: string | undefined;
  let machine = false;
  let machineSeen = false;

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--machine") {
      if (machineSeen) return { ok: false, error: "--machine given more than once" };
      machineSeen = true;
      machine = true;
      continue;
    }
    let key: "--server" | "--data-dir" | undefined;
    let value: string | undefined;
    for (const k of ["--server", "--data-dir"] as const) {
      if (arg === k) {
        key = k;
        if (i + 1 >= argv.length) return { ok: false, error: `${k} needs a value` };
        value = argv[++i];
      } else if (arg.startsWith(k + "=")) {
        key = k;
        value = arg.slice(k.length + 1);
      }
    }
    if (key === undefined || value === undefined) {
      return { ok: false, error: `unknown argument: ${arg}` };
    }
    if (value === "") return { ok: false, error: `${key} needs a non-empty value` };
    if (key === "--server") {
      if (server !== undefined) return { ok: false, error: "--server given more than once" };
      server = value;
    } else {
      if (dataDir !== undefined) return { ok: false, error: "--data-dir given more than once" };
      dataDir = value;
    }
  }

  return {
    ok: true,
    options: {
      server: server ?? "ws://127.0.0.1:8765",
      dataDir: dataDir ?? ".msgdata",
      machine,
    },
  };
}
