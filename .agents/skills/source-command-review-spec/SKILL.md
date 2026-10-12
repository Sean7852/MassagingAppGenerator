---
name: "source-command-review-spec"
description: "Review the spec for gaps that would let two clients behave differently"
---

# source-command-review-spec

Use this skill when the user asks to run the migrated source command `review-spec`.

## Command Template

Use the `spec-reviewer` agent to review `spec/`. When it finishes, show the human the new
items in `spec/OPEN_QUESTIONS.md`, blocking ones first, each with the reviewer's
recommendation. Do not change the spec; suggest `/clarify-spec` to resolve them.
