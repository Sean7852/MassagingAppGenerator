// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

import { parseArgs, USAGE } from "./args.js";
import { Client } from "./client.js";
import { LineSplitter } from "./commands.js";

function main(): void {
  const parsed = parseArgs(process.argv.slice(2));
  if ("error" in parsed) {
    process.stderr.write(`${parsed.error}\n${USAGE}\n`);
    process.exitCode = 2;
    return;
  }

  process.on("uncaughtException", (err) => console.error("internal error:", err));
  process.on("unhandledRejection", (err) => console.error("internal error:", err));

  const client = new Client(parsed);
  const splitter = new LineSplitter((line) => client.pushLine(line));
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk: string) => splitter.push(chunk));
  process.stdin.on("end", () => {
    splitter.end();
    client.pushEof();
  });
  process.stdin.on("error", (err) => console.error("stdin error:", err));
  void client.run();
}

main();
