# Spec

**Spec version: 1** (login, send, receive; online only)

This folder is the source of truth. Any question about how a client behaves is answered here,
not by reading generated code. If the spec and a client disagree, the client is wrong. If the
spec is silent or ambiguous, the spec gets fixed (see [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)).

## Layers

| Layer | Folder | Applies to | Contains |
|---|---|---|---|
| Core | [core/](core/) | every client and the server | protocol, client behavior, CLI contract, defaults |
| Extensions | [extensions/](extensions/) | every client | optional feature modules (none in v1) |
| Platforms | [platforms/](platforms/) | one client | runtime, libraries, layout, build/test/run commands |

A client for platform `P` is generated from: `core/*` + `extensions/*` + `platforms/P.md`.
Conformance scenarios in [../conformance/scenarios/](../conformance/scenarios/) are executable
examples of this spec. When a scenario and the prose disagree, the prose wins and the scenario
is a bug.

Core and extension modules say **what** clients do and must never mention a language.
Platform modules say **how** on one platform and must never change observable behavior.

## Reading order

1. [core/00-overview.md](core/00-overview.md): terms, actors, invariants
2. [core/10-protocol.md](core/10-protocol.md): wire frames between client and server
3. [core/20-client.md](core/20-client.md): client state machine and send/receive rules
4. [core/30-cli.md](core/30-cli.md): the exact stdin/stdout contract
5. [core/90-defaults.md](core/90-defaults.md): what to do when nothing more specific is said
6. `extensions/*.md`, in file-name order
7. `platforms/<platform>.md`

Later files may refine earlier ones only where they say so explicitly.

## Normative words

**MUST**, **MUST NOT**, **SHOULD**, **MAY** are used as in RFC 2119. Anything written as an
exact line, frame or regex in `code` is exact: byte for byte, case-sensitive.

## Changing the spec

- Bump the version at the top of this file for any change to observable behavior.
- Record why in [decisions/](decisions/), one file per spec version.
- Add or update conformance scenarios in the same change.
- A new feature goes in a new `extensions/NN-name.md` that states which core rules it changes.
- A new platform is a new `platforms/<name>.md` with the same front matter keys as the others.

## Ambiguity

Before generation, blocking questions go in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md). The
generator refuses to run while any are open. During generation, the generator never guesses
about anything another client could observe: it stops and reports the question instead.
Choices that are invisible outside one client are recorded in that client's `ASSUMPTIONS.md`.
