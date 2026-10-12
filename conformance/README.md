# Conformance tests

Language-neutral scenarios that drive **real client processes** through a **real server** and
compare their stdout with the CLI contract in [spec/core/30-cli.md](../spec/core/30-cli.md).
Hand-written; not generated.

```bash
python conformance/run.py                      # every scenario, every pairing of built clients
python conformance/run.py --pair py-ts         # one pairing
python conformance/run.py --platform python    # only python with itself (py-py)
python conformance/run.py --scenario basic_exchange
```

Clients must be built first (`python harness/verify.py <platform>` does setup + build + test +
conformance). Platforms and their run commands come from the front matter in
`spec/platforms/*.md`.

## Pairings
A scenario names its clients (`alice`, `bob`, ...). For pairing `A-B`, clients in odd positions
(1st, 3rd, ...) run platform A and the others platform B. So with two platforms there are four
pairings: py-py, ts-ts, py-ts, ts-py. A fresh server is started for every scenario run.

## Scenario format

```yaml
name: basic_exchange
description: Two users send each other a message.
clients: [alice, bob]
steps:
  - alice: /login alice                 # write a line to alice's stdin
  - alice?: LOGGED_IN name=alice        # alice's next stdout line must match
  - bob?any:                            # bob's next N lines, in any order
      - RECV seq={s1} id={m1} from=alice text=hi
      - LOGGED_IN name=bob
  - bob?none: 300                       # no stdout from bob for 300 ms
  - restart: alice                      # close alice's stdin (expects BYE, exit 0), start again
  - crash: alice                        # kill alice's process, start again
  - server: stop                        # kill the server (an outage); `server: start` brings
                                        # it back on the same port, empty (it is in-memory)
```

- Every client gets its own empty data directory (`--data-dir`) per run. `restart` and `crash`
  keep it, so saved state carries over, as it would for a real user.

- `<client>: <line>` writes `<line>` plus `\n` to that client's stdin.
- `<client>?: <pattern>` waits (default 5 s) for that client's **next** stdout line and
  requires it to match. Lines are never skipped, so unexpected output fails the test.
- `<client>?any: [patterns]` takes the next N lines and requires them to match the N
  patterns in some order.
- `<client>?none: <ms>` requires no stdout line within that time.
- Patterns are literal text except `{name}`, which matches one or more non-space characters.
  The first match binds the name; later uses must match the same value.
  `{{` and `}}` are literal braces.
- At the end every client gets `/quit`, must print `BYE` as its next line, and must exit with
  status 0.
