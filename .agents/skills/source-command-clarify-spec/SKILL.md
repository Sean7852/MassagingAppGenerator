---
name: "source-command-clarify-spec"
description: "Resolve open spec questions with the human and write the answers into the spec"
---

# source-command-clarify-spec

Use this skill when the user asks to run the migrated source command `clarify-spec`.

## Command Template

Walk through the unchecked items in `spec/OPEN_QUESTIONS.md` with the human, blocking ones
first. This is the only place where questions about behavior are answered, so that generation
never has to ask.

For each item:
1. Explain the question in plain words, with the options and your recommendation.
2. Ask the human to decide (use AskUserQuestion; batch related items, at most 4 at a time).
3. Write the decision into the right spec module, so the spec answers it without the question.
4. Record it in `spec/decisions/v<version>.md` (who decided, and why).
5. Add or update a conformance scenario when the decision is observable.
6. Check the item in `OPEN_QUESTIONS.md` (`- [x]`).

At the end, bump the spec version in `spec/README.md` if observable behavior changed, run
`python harness/spec_gate.py`, and summarize what changed. Do not regenerate or commit unless
the human asks.
