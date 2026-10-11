# Open questions

The generator refuses to run while the **Blocking** section has an unchecked item (`- [ ]`).
Resolve a question by changing the spec, recording the decision in `decisions/`, and then
checking the item (`- [x]`) or deleting it.

## Blocking

(none)

## Non-blocking

- [ ] Should `login` carry a protocol version so the server can refuse clients built from an
  older spec? Not needed while all clients come from the same spec version. Revisit when the
  first extension changes frames.
