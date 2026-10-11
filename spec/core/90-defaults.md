# 90 — Defaults

Rules for anything the other modules do not cover. They exist so that every client fills the
same gap in the same way.

## Behavior
1. **Do nothing extra.** No features, commands, output lines, frames, retries, timeouts or
   reconnects that the spec does not ask for.
2. **Unknown input from the server is ignored**: unknown frame types, unknown fields, and a
   frame that is not valid JSON or not an object. Ignoring means no output and no state change.
3. **The client never crashes on input.** Any unexpected internal failure is reported on
   stderr, and the client keeps running. It only exits as described in
   [30-cli.md](30-cli.md) (bad arguments, `/quit`, end of input).
4. **Strings are passed through unchanged.** Names, texts and server messages are not trimmed,
   case-folded or normalized. The only change is output escaping.
5. **One event, one action.** Each command or frame is handled completely before the next one.
6. **Frames are written as compact JSON** in a single WebSocket text message. Field order does
   not matter.

## Ambiguity during generation
- If a question affects anything another client or the server could observe (frames, output
  lines, ordering, timing, errors) and the spec does not answer it: **stop and report it**.
  Do not guess.
- If it only affects code inside one client (file names, module structure, which standard
  library function to use): choose, and record the choice in that client's `ASSUMPTIONS.md`.
- Prefer the standard library. Use third-party packages only where a platform module allows them.
