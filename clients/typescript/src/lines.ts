// GENERATED from spec/ by the client-generator agent. Do not edit; change the spec and regenerate.

/**
 * Splits decoded stdin text into lines ending at "\r\n", "\n" or a lone "\r" (30-cli.md § Input).
 * Unlike node:readline it does not end lines at U+2028 or U+2029, which are part of a command.
 */
export class LineSplitter {
  private buffer = "";
  private skipLF = false;

  /** Feeds one chunk; returns the lines completed by it. */
  push(chunk: string): string[] {
    const lines: string[] = [];
    let start = 0;
    let text = this.buffer + chunk;
    if (this.skipLF && text.startsWith("\n")) text = text.slice(1);
    this.skipLF = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (c === "\n") {
        lines.push(text.slice(start, i));
        start = i + 1;
      } else if (c === "\r") {
        lines.push(text.slice(start, i));
        if (i + 1 < text.length) {
          if (text[i + 1] === "\n") i++;
        } else {
          this.skipLF = true; // a "\n" may start the next chunk
        }
        start = i + 1;
      }
    }
    this.buffer = text.slice(start);
    return lines;
  }

  /** End of input: a last line with no line ending is still a line. */
  end(): string[] {
    const rest = this.buffer;
    this.buffer = "";
    return rest === "" ? [] : [rest];
  }
}
