"""Spec gate: refuse to generate while spec/OPEN_QUESTIONS.md has open blocking questions.

    python harness/spec_gate.py        exit 0 if generation may run, 1 if not
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "spec" / "OPEN_QUESTIONS.md"
SPEC_README = ROOT / "spec" / "README.md"


def spec_version() -> str:
    m = re.search(r"\*\*Spec version:\s*([^*]+)\*\*", SPEC_README.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit(f"{SPEC_README}: no '**Spec version: N**' line")
    return m.group(1).strip()


def blocking_questions() -> list[str]:
    """Unchecked items (`- [ ]`) in the '## Blocking' section, first line of each."""
    text = QUESTIONS.read_text(encoding="utf-8")
    m = re.search(r"^## Blocking\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        raise SystemExit(f"{QUESTIONS}: no '## Blocking' section")
    return [line.strip()[6:] for line in m.group(1).splitlines() if line.strip().startswith("- [ ]")]


def check() -> list[str]:
    """Return the reasons generation must not run (empty list: OK)."""
    spec_version()
    return [f"open blocking question: {q}" for q in blocking_questions()]


def main() -> int:
    problems = check()
    for p in problems:
        print(f"GATE  {p}")
    if problems:
        print(f"\nSpec gate closed: resolve {QUESTIONS.relative_to(ROOT)} (try /clarify-spec).")
        return 1
    print(f"Spec gate open: spec version {spec_version()}, no blocking questions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
