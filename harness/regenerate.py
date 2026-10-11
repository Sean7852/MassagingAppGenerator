"""Regenerate clients from the spec, headlessly. The one generation pipeline:
`/generate` in Claude Code runs this script too.

    python harness/regenerate.py --platform <python|typescript|all> [--max-fix-rounds 3]

Per platform:
  1. gate      spec/OPEN_QUESTIONS.md has no open blocking question (harness/spec_gate.py)
  2. clean     delete clients/<p>/ (harness/clean.py)
  3. generate  `claude -p --agent client-generator`, which may only write clients/<p>/
  4. verify    headers, setup, build, unit tests, conformance (harness/verify.py)
  5. fix       `claude -p --agent client-fixer` with the failure report, then verify again,
               at most --max-fix-rounds times
  6. record    clients/<p>/.manifest.json and GENERATED.md (harness/manifest.py)
Then, with more than one client present, every cross pairing (py-ts, ts-py, ...), with fix
rounds for the regenerated platforms if a pairing fails.

Every agent transcript is kept in harness/.runs/<timestamp>/ (not committed).
Exit 0 when every platform passes; 1 on verification failure; 3 when the spec gate is closed
or an agent reported a blocking spec question (BLOCKED.md).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from harness import manifest, spec_gate  # noqa: E402
from harness.clean import clean  # noqa: E402
from harness.platforms import Platform, load_platforms, resolve  # noqa: E402
from harness.verify import verify  # noqa: E402

DEFAULT_MODEL = "claude-opus-5-5"
AGENT_TIMEOUT = 60 * 60
TOOLS_ALLOWED = ["Read", "Write", "Edit", "Glob", "Grep", "TodoWrite",
                 "Bash(python *)", "Bash(npm *)", "Bash(node *)", "Bash(npx *)",
                 "Bash(cd *)", "Bash(ls *)"]
# Variables a Claude Code session sets for its own children. A nested `claude -p` that
# inherits them runs in that session's mode (for example without CLAUDE.md), so drop them,
# but keep explicit credentials.
KEEP_ENV = {"ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"}


class Blocked(Exception):
    pass


def agent_env() -> dict[str, str]:
    env = dict(os.environ)
    if "CLAUDECODE" in env:
        env = {k: v for k, v in env.items()
               if k in KEEP_ENV or not k.startswith(("CLAUDE", "ANTHROPIC"))}
    return env


def denied_tools(p: Platform, platforms: dict[str, Platform]) -> list[str]:
    """The agent for <p> reads the spec and writes clients/<p>/ only."""
    others = [o for o in platforms.values() if o is not p]
    deny = ["Read(./server/**)", "Read(./harness/*.py)"]
    deny += [f"Read(./{o.dir.relative_to(ROOT).as_posix()}/**)" for o in others]
    protected = ["spec/**", "conformance/**", "server/**", "harness/**", ".claude/**",
                 "CLAUDE.md", "AGENTS.md", "README.md"]
    protected += [f"{o.dir.relative_to(ROOT).as_posix()}/**" for o in others]
    for tool in ("Edit", "Write"):
        deny += [f"{tool}(./{path})" for path in protected]
    return deny


def outside_snapshot(p: Platform) -> dict[str, str]:
    """Content hash of every changed or untracked file outside clients/<p>/ (git status)."""
    out = subprocess.run(["git", "status", "--porcelain=v1", "-uall", "-z"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    prefix = p.dir.relative_to(ROOT).as_posix() + "/"
    snap = {}
    for entry in filter(None, out.split("\0")):
        path = entry[3:]
        if path.startswith(prefix):
            continue
        f = ROOT / path
        snap[path] = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else "-"
    return snap


def run_agent(agent: str, prompt: str, p: Platform, platforms: dict[str, Platform],
              model: str, log: Path) -> dict[str, Any]:
    claude = shutil.which("claude")
    if not claude:
        raise SystemExit("`claude` (Claude Code CLI) is not on PATH")
    cmd = [claude, "-p", prompt, "--agent", agent, "--model", model,
           "--permission-mode", "acceptEdits",
           "--allowedTools", *TOOLS_ALLOWED,
           "--disallowedTools", *denied_tools(p, platforms),
           "--output-format", "stream-json", "--verbose", "--no-session-persistence"]
    tag = f"[{agent} {p.name}]"
    print(f"{tag} started (log: {log.relative_to(ROOT)})", flush=True)
    before = outside_snapshot(p)
    start = time.monotonic()
    result: dict[str, Any] = {}
    with log.open("w", encoding="utf-8") as f, subprocess.Popen(
            cmd, cwd=ROOT, env=agent_env(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace") as proc:
        try:
            for line in proc.stdout:
                f.write(line)
                event = _parse(line)
                if event.get("type") == "assistant":
                    for item in event.get("message", {}).get("content", []):
                        if item.get("type") == "tool_use":
                            print(f"{tag} {_describe(item)}", flush=True)
                elif event.get("type") == "result":
                    result = event
            proc.wait(timeout=max(1, AGENT_TIMEOUT - (time.monotonic() - start)))
        except subprocess.TimeoutExpired:
            proc.kill()
            raise SystemExit(f"{tag} timed out after {AGENT_TIMEOUT}s")
    minutes = (time.monotonic() - start) / 60
    cost = result.get("total_cost_usd", 0.0)
    print(f"{tag} finished in {minutes:.1f} min, {result.get('num_turns', '?')} turns, "
          f"${cost:.2f}, exit {proc.returncode}", flush=True)
    if result.get("is_error") or proc.returncode != 0:
        print(f"{tag} reported an error: {str(result.get('result', ''))[:500]}", flush=True)

    after = outside_snapshot(p)
    changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    if changed:
        raise SystemExit(f"{tag} changed files outside {p.dir.relative_to(ROOT)}: "
                         f"{sorted(changed)}. Regeneration boundary violated; inspect and revert.")
    blocked = p.dir / "BLOCKED.md"
    if blocked.exists():
        raise Blocked(f"{p.name}: the agent reported a spec question:\n\n"
                      + blocked.read_text(encoding="utf-8"))
    return {"cost_usd": cost, "turns": result.get("num_turns"), "minutes": round(minutes, 1)}


def _parse(line: str) -> dict[str, Any]:
    try:
        event = json.loads(line)
        return event if isinstance(event, dict) else {}
    except json.JSONDecodeError:
        return {}


def _describe(tool_use: dict[str, Any]) -> str:
    name, args = tool_use.get("name", "?"), tool_use.get("input", {})
    detail = args.get("file_path") or args.get("command") or args.get("pattern") or ""
    detail = str(detail).replace(str(ROOT), "").replace("\\", "/").lstrip("/").splitlines()
    return f"{name} {detail[0][:100] if detail else ''}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--platform", default="all", help="python, typescript, short name, or all")
    ap.add_argument("--max-fix-rounds", type=int, default=3)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args()

    platforms = load_platforms()
    targets = resolve(args.platform, platforms)
    problems = spec_gate.check()
    if problems:
        print("\n".join(f"GATE  {x}" for x in problems))
        print("Spec gate closed; nothing was generated. Resolve spec/OPEN_QUESTIONS.md first.")
        return 3
    print(f"Spec version {spec_gate.spec_version()}; regenerating: "
          f"{', '.join(p.name for p in targets)}; model {args.model}", flush=True)

    run_dir = ROOT / "harness" / ".runs" / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True)
    stats: dict[str, dict[str, Any]] = {}
    passed: dict[str, bool] = {}
    try:
        for p in targets:
            print(f"\n=== {p.name} ===", flush=True)
            clean(p)
            gen = run_agent("client-generator",
                            f"Generate the `{p.name}` client into clients/{p.name}/ from the spec. "
                            f"Platform: {p.name}.",
                            p, platforms, args.model, run_dir / f"{p.name}-generate.jsonl")
            stats[p.name] = {"generate": gen, "fix_rounds": [], "rounds_used": 0}
            passed[p.name] = fix_until_green(p, [p], platforms, args, run_dir, stats, cross=False)

        present = [p for p in platforms.values() if p.exists()]
        if len(present) > 1 and all(passed.values()):
            print("\n=== cross-client ===", flush=True)
            ok = False
            for _ in range(args.max_fix_rounds + 1):
                ok, _, cross, report = verify(present, cross=True, report_name="cross")
                if ok or not any(stats[p.name]["rounds_used"] < args.max_fix_rounds for p in targets):
                    break
                for p in targets:
                    if stats[p.name]["rounds_used"] < args.max_fix_rounds:
                        fix(p, report, platforms, args, run_dir, stats)
            for p in targets:
                passed[p.name] = passed[p.name] and ok
                stats[p.name]["cross"] = "pass" if ok else "fail"
    except Blocked as e:
        print(f"\nBLOCKED  {e}\nAnswer it in the spec (try /clarify-spec), then regenerate.")
        return 3

    for p in targets:
        s = stats[p.name]
        manifest.write(p, {
            "verify": "pass" if passed[p.name] else "fail",
            "cross": s.get("cross", "not run"),
            "fix_rounds": s["rounds_used"],
            "generator": {"model": args.model, "agent": "client-generator",
                          "cost_usd": round(s["generate"]["cost_usd"]
                                            + sum(r["cost_usd"] for r in s["fix_rounds"]), 2)},
        })

    print("\n=== summary ===")
    for p in targets:
        s = stats[p.name]
        cost = s["generate"]["cost_usd"] + sum(r["cost_usd"] for r in s["fix_rounds"])
        print(f"{'PASS' if passed[p.name] else 'FAIL'}  {p.name:<12} fix rounds {s['rounds_used']}, "
              f"cross {s.get('cross', 'not run')}, ${cost:.2f}")
    print(f"Logs: {run_dir.relative_to(ROOT)}")
    return 0 if all(passed.values()) else 1


def fix_until_green(p: Platform, scope: list[Platform], platforms: dict[str, Platform],
                    args: argparse.Namespace, run_dir: Path, stats: dict[str, Any],
                    cross: bool) -> bool:
    while True:
        ok, _, _, report = verify(scope, cross=cross, report_name=f"verify-{p.name}")
        if ok:
            return True
        if stats[p.name]["rounds_used"] >= args.max_fix_rounds:
            print(f"{p.name}: still failing after {args.max_fix_rounds} fix rounds; see {report.relative_to(ROOT)}")
            return False
        fix(p, report, platforms, args, run_dir, stats)


def fix(p: Platform, report: Path, platforms: dict[str, Platform], args: argparse.Namespace,
        run_dir: Path, stats: dict[str, Any]) -> None:
    n = stats[p.name]["rounds_used"] + 1
    stats[p.name]["rounds_used"] = n
    rel = report.relative_to(ROOT).as_posix()
    keep = run_dir / f"{p.name}-fix{n}-report.md"
    keep.write_text(report.read_text(encoding="utf-8"), encoding="utf-8")
    stats[p.name]["fix_rounds"].append(run_agent(
        "client-fixer", f"Platform: {p.name}. Failure report: {rel}. Fix clients/{p.name}/.",
        p, platforms, args.model, run_dir / f"{p.name}-fix{n}.jsonl"))


if __name__ == "__main__":
    sys.exit(main())
