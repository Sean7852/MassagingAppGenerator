---
# Read by the harness (harness/platforms.py). Commands run with clients/typescript/ as the
# working directory.
platform: typescript
short: ts
dir: clients/typescript
sources: ".ts"        # files that must carry the generated-file header
ignore: [node_modules, dist]  # build output, never checked or hashed
setup:
  - npm install --no-audit --no-fund --loglevel=error
build:
  - npm run build --silent
test:
  - npm test --silent
run: node dist/main.js
---

# Platform — TypeScript (Node.js)

How to build the client in TypeScript on Node.js. Behavior comes only from `spec/core` and
`spec/extensions`; nothing here may change what the client prints or sends.

## Runtime and libraries
- Node.js **24**, ES modules (`"type": "module"` in `package.json`).
- Runtime dependency: exactly one package, `ws` (`^8.18.0`).
- Dev dependencies, exactly: `typescript` (`~5.9.3`), `@types/ws` (`^8.18.0`),
  `@types/node` (`^24.0.0`).
- Message ids: `crypto.randomUUID()` from `node:crypto` (already lowercase).
- JSON: `JSON.stringify(frame)`.

## Layout
```
clients/typescript/
  package.json         scripts: "build": "tsc", "test": "node --test dist/test/*.test.js"
  package-lock.json    created by npm install, committed
  tsconfig.json        strict, target ES2023, module/moduleResolution NodeNext,
                       rootDir "src", outDir "dist"
  src/
    main.ts            entry point
    ...                module split is up to the generator
    test/*.test.ts     tests using node:test and node:assert
```
- `dist/` and `node_modules/` are build output and are not committed (add a `.gitignore`).
- Every `.ts` file starts with the generated-file header (see the generator rules).
- Relative imports use the `.js` extension, as NodeNext requires.

## Must-follow implementation rules
These avoid known platform pitfalls. They do not change behavior.
1. **stdin**: `process.stdin.setEncoding("utf8")` and `readline.createInterface({ input:
   process.stdin, crlfDelay: Infinity, terminal: false })`. Each `line` event is one command
   (readline ends lines at `\r\n`, `\n` or `\r` and removes the ending, as the CLI spec says). The `close` event is end of input.
2. **Output** goes through one function that calls `process.stdout.write(line + "\n")`.
   Nothing else writes to stdout (`console.log` is not used; diagnostics use `console.error`).
3. **Exit**: after `BYE`, close the WebSocket and the readline interface and let the process
   end on its own with `process.exitCode = 0`. Do not call `process.exit()` while output may
   still be buffered (stdout to a pipe is asynchronous on some systems).
4. **Connecting**: `new WebSocket(url, { maxPayload: 64 * 1024, handshakeTimeout: 5000 })`
   from `ws`. Wait for `open` before sending `login`. An `error` or `close` before `open`
   (including an invalid URL throwing in the constructor) is `connect_failed`.
5. **Events one at a time**: stdin lines and WebSocket messages are put on one queue and
   handled in order by a single async loop, so a handler never interleaves with another.
6. **Text frames**: send strings with `ws.send(json)`; when receiving, convert the `data`
   (`Buffer`) to a string with UTF-8.
7. Argument parsing with `node:util` `parseArgs`. On bad arguments write usage to stderr and
   set the exit status to 2.
8. **Saving** ([40-storage.md](../core/40-storage.md)): use the synchronous `node:fs` calls,
   inside the event handler, before the output line: `mkdirSync(dir, { recursive: true })`,
   `writeFileSync(tmp, JSON.stringify(state), "utf8")`, then `renameSync(tmp, file)` (it
   replaces the target on Windows too). Loading uses `readFileSync` at startup.
9. **Exit with status 1** (bad saved state): write the message to stderr, then set
   `process.exitCode = 1` and stop starting up, instead of calling `process.exit(1)`.

## Tests
`src/test/` contains `node:test` tests that need no server and no network, covering at least:
stdin command parsing (every row of the parsing table in 30-cli.md) and output escaping.
