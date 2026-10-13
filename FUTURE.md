# Future

What we would do next, roughly in order of value. This was a time-boxed exercise; the design
reasons behind what exists are in [DESIGN.md](DESIGN.md).

## 1. Harness and quality

- **Run the conformance suite in CI.** A GitHub Actions job running `python harness/verify.py
  all` on every push (no AI needed, a few minutes), and a scheduled job that regenerates both
  clients from scratch and reports whether they still pass. Today both are run by hand.
- **Measure how repeatable generation is.** Regenerate each client several times from the
  same spec and compare: do all runs pass? How much does the code differ? This turns
  "regeneration works" from a few observations into a number.
- **A third platform.** Add `spec/platforms/<language>.md` for, say, Go or Kotlin, and
  regenerate. That would test the platform layer the way v3 tested the extension layer.
- **A cost cap per run.** Pass Claude Code's `--max-budget-usd` to every agent run, so a
  confused generator cannot run away. Label printed costs as API-price estimates
  everywhere (on a subscription they use plan limits, not money).
- **Generate platforms in parallel.** They are independent until the cross-client check;
  running them side by side would halve the wall-clock time.
- **Cover the rules no scenario reaches yet** (review item N11): a fake-server step in the
  runner (to send broken frames, stall, or drop pongs, which would also test the keep-alive),
  a step that writes or inspects `state.json` (bad files, files written by the other
  platform), and checks for exit statuses 1 and 2.
- **A cheaper review loop.** Keep `/review-spec` manual, but record which spec version was
  last reviewed, so `/generate` can *warn* (not block) when a changed spec was never
  reviewed.

## 2. Spec

- **Close the remaining non-blocking review items**:
  - N5: a server that confirms a different name than the one typed at `/login`;
  - N9: two processes logged in as the same user share one folder.
- **Confirm the pending AI defaults:** D43 (the client checks the `/login` name) and D44
  (`.msgdata/` ignored by Git).
- **A protocol version in `login`**, so a server can refuse clients built from an older spec,
  once extensions start changing existing frames rather than adding new ones.
- **Ctrl+C and SIGTERM** (B13, out of scope today): treat them like `/quit`.
- **Remember shown messages across restarts** (D19), so a message is never shown twice.

## 3. Features (each a new extension module)

- **Reactions:** `/react #<seq> <emoji>`, held and delivered like receipts.
- **Group conversations:** membership, fan-out on the server, ordering per group. The
  largest one, and the best stress test of the extension layer.
- **Attachments:** size limits and chunking would test the protocol more than the client.
- **Automatic reconnect** with a fixed backoff, as an option next to `/online`. It needs exact
  timing rules to stay testable across both clients.
- **Logout and switching users** without quitting the client (today: `/quit`, start again,
  `/login` as someone else).

## 4. User interface

- **A GUI as a thin layer** over the same client core: a window that sends the same commands
  and reads the `--machine` lines. The tested behavior stays in the CLI, and the GUI adds no
  new rules to keep identical across languages.

## 5. Server (out of scope for this exercise)

- Persistence across restarts, authentication instead of "identify by name", rate limits,
  and running more than one process. Persistence would not change the protocol; authentication
  would extend `login` with credentials, as an extension module.
