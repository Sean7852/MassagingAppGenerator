// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

export type ServerFrame =
  | { type: "login_ok"; name: string }
  | { type: "ack"; id: string; seq: number }
  | { type: "deliver"; seq: number; id: string; from: string; text: string }
  | { type: "error"; code: string; message: string; ref?: string };

function isSeq(v: unknown): v is number {
  return typeof v === "number" && Number.isInteger(v) && v >= 1 && v <= Number.MAX_SAFE_INTEGER;
}

/**
 * Parses one text frame from the server. Returns null for anything to ignore
 * (not JSON, not an object, unknown type, or a known type that breaks its rules).
 */
export function parseServerFrame(text: string): ServerFrame | null {
  let raw: unknown;
  try {
    raw = JSON.parse(text);
  } catch {
    return null;
  }
  if (typeof raw !== "object" || raw === null || Array.isArray(raw)) return null;
  const f = raw as Record<string, unknown>;
  switch (f.type) {
    case "login_ok":
      if (typeof f.name !== "string") return null;
      return { type: "login_ok", name: f.name };
    case "ack":
      if (typeof f.id !== "string" || !isSeq(f.seq)) return null;
      return { type: "ack", id: f.id, seq: f.seq };
    case "deliver":
      if (!isSeq(f.seq) || typeof f.id !== "string" || typeof f.from !== "string" || typeof f.text !== "string") {
        return null;
      }
      return { type: "deliver", seq: f.seq, id: f.id, from: f.from, text: f.text };
    case "error": {
      if (typeof f.code !== "string" || typeof f.message !== "string") return null;
      if (f.ref === undefined || f.ref === null) return { type: "error", code: f.code, message: f.message };
      if (typeof f.ref !== "string") return null;
      return { type: "error", code: f.code, message: f.message, ref: f.ref };
    }
    default:
      return null;
  }
}
