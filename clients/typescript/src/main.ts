// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { parseArgs, USAGE } from "./args.js";
import { Client } from "./client.js";
import { LineSplitter } from "./commands.js";
import { loadState, type State } from "./storage.js";

function main(): void {
  const args = parseArgs(process.argv.slice(2));
  if (!args.ok) {
    console.error(`${args.error}\n${USAGE}`);
    process.exitCode = 2;
    return;
  }
  const { server, dataDir, machine } = args.options;

  let state: State;
  try {
    state = loadState(dataDir);
  } catch (e) {
    console.error((e as Error).message);
    process.exitCode = 1;
    return;
  }

  // The client never crashes on input: report unexpected failures and keep running.
  process.on("uncaughtException", (e) => console.error("internal error:", e));
  process.on("unhandledRejection", (e) => console.error("internal error:", e));

  const stdin = process.stdin;
  const client = new Client({
    server,
    dataDir,
    machine,
    name: state.name,
    outbox: state.outbox,
    onStop: () => {
      stdin.removeAllListeners("data");
      stdin.removeAllListeners("end");
      stdin.pause();
      stdin.destroy();
    },
  });

  const splitter = new LineSplitter((line) => client.pushLine(line));
  stdin.setEncoding("utf8");
  stdin.on("data", (chunk: string) => splitter.push(chunk));
  stdin.on("end", () => {
    splitter.end();
    client.pushEof();
  });

  void client.run();
}

main();
