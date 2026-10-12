"""Verify generated clients: boundary checks, setup, build, unit tests, conformance.

    python harness/verify.py <python|typescript|all> [--no-cross]

For each platform: generated-file headers present, no BLOCKED.md, the setup/build/test commands
from spec/platforms/<p>.md, then conformance against itself. With more than one passing
platform, also every cross pairing (py-ts, ts-py, ...). Writes a Markdown report (path printed
at the end) that the fixer agent reads. Exit 0 only if everything passed.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from harness import manifest  # noqa: E402
from harness.platforms import Platform, resolve  # noqa: E402

RUNS = ROOT / "harness" / ".runs"
CONFORMANCE_REPORT = ROOT / "conformance" / ".runs" / "report.md"
HEADER = "GENERATED from spec/ by the client-generator agent"
COMMAND_TIMEOUT = 900
OUTPUT_TAIL = 150


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class PlatformResult:
    platform: Platform
    checks: list[Check] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)


def run_command(p: Platform, command: str) -> Check:
    try:
        out = subprocess.run(p.argv(command), cwd=p.dir, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=COMMAND_TIMEOUT)
    except FileNotFoundError as e:
        return Check(command, False, str(e))
    except subprocess.TimeoutExpired:
        return Check(command, False, f"timed out after {COMMAND_TIMEOUT}s")
    text = (out.stdout + out.stderr).strip()
    tail = "\n".join(text.splitlines()[-OUTPUT_TAIL:])
    return Check(command, out.returncode == 0, tail if out.returncode else "")


def run_conformance(args: list[str]) -> Check:
    out = subprocess.run([sys.executable, str(ROOT / "conformance" / "run.py"), *args],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                         errors="replace")
    summary = out.stdout.strip()
    report = CONFORMANCE_REPORT.read_text(encoding="utf-8") if CONFORMANCE_REPORT.exists() else ""
    detail = summary if out.returncode == 0 else f"{summary}\n{out.stderr.strip()}\n\n{report}"
    return Check("conformance " + " ".join(args), out.returncode == 0, detail.strip())


def boundary_checks(p: Platform) -> list[Check]:
    checks = []
    blocked = p.dir / "BLOCKED.md"
    checks.append(Check("no BLOCKED.md", not blocked.exists(),
                        blocked.read_text(encoding="utf-8") if blocked.exists() else ""))
    missing = []
    for f in p.source_files():
        first = f.read_text(encoding="utf-8", errors="replace").split("\n", 1)[0]
        if HEADER not in first:
            missing.append(f.relative_to(ROOT).as_posix())
    sources = p.source_files()
    checks.append(Check("generated-file headers", bool(sources) and not missing,
                        "no source files" if not sources else "\n".join(missing)))
    checks.append(Check("ASSUMPTIONS.md present", (p.dir / "ASSUMPTIONS.md").exists()))
    return checks


def verify_platform(p: Platform) -> PlatformResult:
    r = PlatformResult(p)
    if not p.exists():
        r.checks.append(Check("client folder exists", False, f"{p.dir} is missing"))
        return r
    r.checks += boundary_checks(p)
    for command in (*p.setup, *p.build, *p.test):
        r.checks.append(run_command(p, command))
        if not r.checks[-1].ok:
            return r
    r.checks.append(run_conformance(["--platform", p.name]))
    return r


def verify(platforms: list[Platform], cross: bool = True,
           report_name: str = "verify") -> tuple[bool, list[PlatformResult], list[Check], Path]:
    results = []
    for p in platforms:
        r = verify_platform(p)
        results.append(r)
        print(f"{'PASS' if r.ok else 'FAIL'}  {p.name}"
              + "".join(f"\n      FAIL {c.name}" for c in r.checks if not c.ok), flush=True)
    cross_checks = []
    passing = [r.platform for r in results if r.ok]
    if cross and len(passing) > 1:
        for a in passing:
            for b in passing:
                if a is not b:
                    c = run_conformance(["--pair", f"{a.short}-{b.short}"])
                    cross_checks.append(c)
                    print(f"{'PASS' if c.ok else 'FAIL'}  cross {a.short}-{b.short}", flush=True)
    ok = all(r.ok for r in results) and all(c.ok for c in cross_checks)
    return ok, results, cross_checks, write_report(report_name, results, cross_checks)


def write_report(name: str, results: list[PlatformResult], cross: list[Check]) -> Path:
    RUNS.mkdir(parents=True, exist_ok=True)
    out = ["# Verification report\n"]
    for r in results:
        out.append(f"## {r.platform.name}: {'PASS' if r.ok else 'FAIL'}\n")
        for c in r.checks:
            out.append(f"- {'ok  ' if c.ok else 'FAIL'} {c.name}")
        stale = manifest.check(r.platform) if r.platform.exists() else None
        if stale:
            out.append(f"- note: {stale}")
        for c in r.checks:
            if not c.ok and c.detail:
                out += [f"\n### FAIL {c.name}\n", "````", c.detail, "````"]
        out.append("")
    if cross:
        out.append("## Cross-client conformance\n")
        out += [f"- {'ok  ' if c.ok else 'FAIL'} {c.name}" for c in cross]
        for c in cross:
            if not c.ok:
                out += [f"\n### FAIL {c.name}\n", "````", c.detail, "````"]
    path = RUNS / f"{name}.md"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify generated clients")
    ap.add_argument("platform", help="python, typescript, a short name, or all")
    ap.add_argument("--no-cross", action="store_true", help="skip cross-client pairings")
    args = ap.parse_args()
    platforms = resolve(args.platform)
    if args.platform == "all":
        for p in platforms:
            if not p.exists():
                print(f"skip  {p.name}: no client at {p.dir.relative_to(ROOT)}")
        platforms = [p for p in platforms if p.exists()]
        if not platforms:
            raise SystemExit("no generated clients; run harness/regenerate.py first")
    ok, _, _, report = verify(platforms, cross=not args.no_cross)
    print(f"\n{'ALL PASSED' if ok else 'FAILED'}. Report: {report.relative_to(ROOT)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
