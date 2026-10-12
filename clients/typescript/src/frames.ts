// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

/** Server frames the client understands, after validation (90-defaults.md rule 2). */
export type ServerFrame =
  | { type: "login_ok"; name: string }
  | { type: "ack"; id: string; seq: number }
  | { type: "deliver"; seq: number; id: string; from: string; text: string }
  | { type: "error"; code: string; message: string; ref?: string }
  | { type: "receipt"; seq: number; msgSeq: number; msgId: string; by: string };

export function isSeq(v: unknown): v is number {
  return typeof v === "number" && Number.isInteger(v) && v >= 1 && v <= Number.MAX_SAFE_INTEGER;
}

const isStr = (v: unknown): v is string => typeof v === "string";

/**
 * Parses one text frame. Returns null for anything to ignore: not JSON, not an object,
 * unknown type, or a known type that breaks its rules.
 */
export function parseServerFrame(raw: string): ServerFrame | null {
  let d: unknown;
  try {
    d = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof d !== "object" || d === null || Array.isArray(d)) return null;
  const f = d as Record<string, unknown>;
  switch (f.type) {
    case "login_ok":
      return isStr(f.name) ? { type: "login_ok", name: f.name } : null;
    case "ack":
      return isStr(f.id) && isSeq(f.seq) ? { type: "ack", id: f.id, seq: f.seq } : null;
    case "deliver":
      return isSeq(f.seq) && isStr(f.id) && isStr(f.from) && isStr(f.text)
        ? { type: "deliver", seq: f.seq, id: f.id, from: f.from, text: f.text }
        : null;
    case "error": {
      if (!isStr(f.code) || !isStr(f.message)) return null;
      if (f.ref === undefined || f.ref === null) return { type: "error", code: f.code, message: f.message };
      if (!isStr(f.ref)) return null;
      return { type: "error", code: f.code, message: f.message, ref: f.ref };
    }
    case "receipt":
      return isSeq(f.seq) && isSeq(f.msg_seq) && isStr(f.msg_id) && isStr(f.by)
        ? { type: "receipt", seq: f.seq, msgSeq: f.msg_seq, msgId: f.msg_id, by: f.by }
        : null;
    default:
      return null;
  }
}
