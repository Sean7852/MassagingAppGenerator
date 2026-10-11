# Messaging System - Analysis and Implementation Plan

## Part 1: Understanding the Assignment

At its core, you are building a meta-system rather than just writing a messaging app.

- **The deliverable:** A code generator driven by Codex, plus a precise written specification. If someone deletes the client code and runs your generator using the specification, it must recreate working clients.
- **The application:** A simple chat server and two clients in different languages (for example, Python and TypeScript running on Node.js, or Python and Swift). These are examples; the language choices are not finalized.
- **The constraint:** Build an agentic harness - project instructions in `AGENTS.md`, prompts, rules, and scripts - that tells Codex how to build and test the app based on your specification.

## Part 2: What Is a Harness?

A harness is the scaffolding, configuration, and instructions you give an AI coding tool so it follows project rules, uses the right file paths, and knows how to test its work.

For this project, the harness will consist of a root `AGENTS.md`, reusable prompts, and a script or documented workflow that starts generation with Codex. The specification describes what to build; the harness describes how to generate and validate it.

Codex supports project instructions in `AGENTS.md`; see the [official OpenAI documentation](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

## Part 3: The First MVP - A 12-Hour Plan

With only 12 hours, prioritize a small working system. Build in vertical slices instead of attempting offline queueing and both clients at once.

### Step 1: Foundation and Server (Hours 1-2)

- Write a minimal local server in Python, using FastAPI or WebSockets/HTTP, that accepts a message from User A and forwards it to User B.
- Use in-memory storage; no database is needed for this initial server.
- Create a root `AGENTS.md` describing the project structure, chosen languages, and commands to test the server. For example, Client 1 could use Python and Client 2 could use JavaScript on Node.js; choose languages that are easy to run locally.

### Step 2: Core Specification and Client 1 (Hours 3-5)

- Write `SPEC.md` describing the protocol, such as JSON payloads over WebSockets or HTTP POST/GET polling.
- Prompt Codex to generate Client 1, for example a Python CLI, that can register a name, send a message, and poll for or receive messages.

### Step 3: Client 2 and Basic Messaging Loop (Hours 6-8)

- Prompt Codex to generate Client 2, for example a Node.js CLI, following the same `SPEC.md`.
- Manually test that Client 1 can communicate with Client 2 through the local server.

### Step 4: Offline Queue MVP (Hours 9-10)

- Update `SPEC.md` to define local message queueing. For example, if a network call fails, save outgoing messages to a local JSON file or SQLite database and retry at a specified interval.
- Have Codex implement queueing and flushing in both clients.

### Step 5: Packaging and Documentation (Hours 11-12)

- Write a clear project `README.md` explaining how to run the generator, which files form the regeneration boundary, and how to test the result.
- Create `DESIGN.md` explaining architectural choices and a brief `FUTURE.md`.
- Package the repository into a clean ZIP archive.

## Related Documentation

See [README-CODEX.md](README-CODEX.md) for the planned Codex workflow and the distinction between project instructions and the specification.
