---
description: Regenerate clients from the spec (gate, clean, generate, verify, fix, manifest)
argument-hint: "<python|typescript|all>"
---

Regenerate the client(s) for platform `$ARGUMENTS` (default `all`) by running the harness
pipeline. Do not generate or edit client code yourself in this session: the pipeline runs the
`client-generator` and `client-fixer` agents headlessly so that every run is the same.

1. Run `python harness/regenerate.py --platform $ARGUMENTS` from the repo root, in the
   background (it takes several minutes per platform), and wait for it to finish.
2. Report the result: per platform, pass or fail, fix rounds used, conformance summary, and
   cost, all from the script's final summary.
3. If it stopped at the spec gate or a client wrote `BLOCKED.md`, show the open question(s)
   to the human and suggest `/clarify-spec`. Do not answer them yourself.
4. If it failed verification after the last fix round, show the failing scenarios from
   `conformance/.runs/report.md` and say whether the cause looks like the client, the spec or
   the scenario.
5. Do not commit. Generated output is committed on its own with a `gen:` prefix when the human
   asks.
