# Codex Workflow for the Messaging System Assignment

This assignment will use **Codex** to generate the messaging clients from a written specification and reusable project instructions.

## Current Status

The repository is in the planning stage. The server, clients, specification, generation scripts, and tests have not been implemented. This README describes the intended workflow; it is not a runnable setup guide yet.

Read [the implementation plan](<Messaging System - Analysis and Implementation Plan.md>) for the original five-step, 12-hour schedule. The existing [project README](README.md) remains the repository overview.

## Planned Files

| File | Purpose |
| --- | --- |
| `AGENTS.md` | Give Codex repository instructions: project structure, chosen languages, generation boundaries, and build/test commands. |
| `SPEC.md` | Define the messaging protocol and required client behavior. |
| Reusable generation prompts and scripts | Tell Codex which client to generate, where to put it, and how to validate it. Exact filenames and commands will be defined during implementation. |
| `README.md` | Document prerequisites, generation, execution, testing, and regeneration. |
| `DESIGN.md` | Explain architectural choices. |
| `FUTURE.md` | Record deferred improvements. |

Only the plan and README documents exist at this stage; the other files above are planned deliverables.

## Intended Workflow

1. Work with Codex in this repository and follow the implementation plan.
2. Record the selected languages, project layout, and validation commands in a root `AGENTS.md`.
3. Write the messaging contract in `SPEC.md`.
4. Use reusable prompts to ask Codex to generate each client from that specification.
5. Build and test the generated clients against the server, then add the planned offline queue behavior.
6. Document the exact generation and test commands, including which client files can be removed and regenerated.

A reusable prompt can follow this structure once the referenced files exist:

> Generate the requested client from SPEC.md, following AGENTS.md. Use the language and output directory recorded in the project instructions. Run the documented build and validation commands and report the results.

`AGENTS.md` supplies instructions; the generation workflow must still invoke Codex and validate its output. See [OpenAI's AGENTS.md documentation](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

## Technology Choices

Codex is the selected coding agent. The client languages and server stack remain planning choices; examples in the plan are not fixed requirements. C# on .NET is also an option discussed for a client. The two-client, different-language design remains as described in the plan.
