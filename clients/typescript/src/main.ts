// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { parseArgv, USAGE } from "./args.js";
import { Client } from "./client.js";
import { LineSplitter } from "./lines.js";
import { writeLine } from "./output.js";
import { loadState } from "./storage.js";

function main(): void {
  const args = parseArgv(process.argv.slice(2));
  if ("error" in args) {
    console.error(`error: ${args.error}\n${USAGE}`);
    process.exitCode = 2;
    return;
  }

  const saved = loadState(args.dataDir);
  if ("error" in saved) {
    console.error(saved.error);
    process.exitCode = 1;
    return;
  }

  process.on("uncaughtException", (e) => console.error("internal error:", e));

  const stopInput = () => {
    process.stdin.removeAllListeners("data");
    process.stdin.removeAllListeners("end");
    process.stdin.destroy();
  };

  const client = new Client({
    server: args.server,
    dataDir: args.dataDir,
    machine: args.machine,
    saved,
    write: writeLine,
    onQuit: () => {
      stopInput();
      process.exitCode = 0;
    },
    onFatal: (message) => {
      console.error(message);
      stopInput();
      process.stdout.write("", () => process.exit(1));
    },
  });

  const splitter = new LineSplitter();
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk: string) => {
    for (const line of splitter.push(chunk)) client.line(line);
  });
  process.stdin.on("end", () => {
    for (const line of splitter.end()) client.line(line);
    client.eof();
  });
  process.stdin.on("error", (e) => console.error("stdin error:", e));
  client.start();
}

main();
