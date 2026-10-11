---
description: Build, test and run conformance for existing clients without regenerating
argument-hint: "<python|typescript|all>"
---

Run `python harness/verify.py $ARGUMENTS` (default `all`) from the repo root and report, per
platform, setup/build/test results and the conformance summary (all pairings when more than
one platform is verified). On failure, summarize the failing steps from the report path the
script prints. Do not edit `clients/`; if a client is wrong, the fix is `/generate`.
