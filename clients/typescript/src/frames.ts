// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

/** A server frame that passed validation (90-defaults.md rule 2). */
export type ServerFrame =
  | { type: "login_ok"; name: string }
  | { type: "ack"; id: string; seq: number }
  | { type: "deliver"; seq: number; id: string; from: string; text: string }
  | { type: "error"; code: string; message: string; ref?: string }
  | { type: "receipt"; seq: number; msg_seq: number; msg_id: string; by: string };

export function isSeq(v: unknown): v is number {
  return typeof v === "number" && Number.isInteger(v) && v >= 1 && v <= Number.MAX_SAFE_INTEGER;
}

/** Parses and validates one text frame. Returns null for broken or unknown frames. */
export function parseFrame(raw: string): ServerFrame | null {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof data !== "object" || data === null || Array.isArray(data)) return null;
  const f = data as Record<string, unknown>;
  const str = (k: string): boolean => typeof f[k] === "string";
  switch (f.type) {
    case "login_ok":
      return str("name") ? { type: "login_ok", name: f.name as string } : null;
    case "ack":
      return str("id") && isSeq(f.seq) ? { type: "ack", id: f.id as string, seq: f.seq } : null;
    case "deliver":
      if (!isSeq(f.seq) || !str("id") || !str("from") || !str("text")) return null;
      return { type: "deliver", seq: f.seq, id: f.id as string, from: f.from as string, text: f.text as string };
    case "error": {
      if (!str("code") || !str("message")) return null;
      if (f.ref === undefined || f.ref === null) {
        return { type: "error", code: f.code as string, message: f.message as string };
      }
      if (typeof f.ref !== "string") return null;
      return { type: "error", code: f.code as string, message: f.message as string, ref: f.ref };
    }
    case "receipt":
      if (!isSeq(f.seq) || !isSeq(f.msg_seq) || !str("msg_id") || !str("by")) return null;
      return { type: "receipt", seq: f.seq, msg_seq: f.msg_seq, msg_id: f.msg_id as string, by: f.by as string };
    default:
      return null;
  }
}
