"""Conformance runner: drives real client processes through a real server.

Hand-written. Scenario format and usage: conformance/README.md.
Exit status 0 when every run passes, 1 otherwise. A Markdown report of the last run is written
to conformance/.runs/report.md (read by the harness's fixer step).
"""

from __future__ import annotations

import argparse
import itertools
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from harness.platforms import Platform, load_platforms, resolve  # noqa: E402

SCENARIOS = ROOT / "conformance" / "scenarios"
RUNS = ROOT / "conformance" / ".runs"
SERVER = ROOT / "server" / "server.py"
LINE_TIMEOUT = 5.0
EXIT_TIMEOUT = 5.0
EOF = object()


class StepFailed(Exception):
    pass


# ---- transcript -------------------------------------------------------------------------

@dataclass
class Transcript:
    start: float = field(default_factory=time.monotonic)
    events: list[str] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def add(self, who: str, kind: str, text: str) -> None:
        with self.lock:
            self.events.append(f"{time.monotonic() - self.start:7.3f}  {who:<10} {kind} {text}")


# ---- processes --------------------------------------------------------------------------

class Client:
    def __init__(self, role: str, platform: Platform, url: str, log: Transcript, data_dir: Path):
        self.role, self.platform, self.url, self.log = role, platform, url, log
        self.data_dir = data_dir
        self.label = f"{role}[{platform.short}]"
        self.lines: queue.Queue[Any] = queue.Queue()
        self.start()

    def start(self) -> None:
        argv = self.platform.argv(self.platform.run) + ["--server", self.url,
                                                        "--data-dir", str(self.data_dir)]
        self.log.add(self.label, "##", "start: " + " ".join(argv[1:]))
        self.proc = subprocess.Popen(argv, cwd=self.platform.dir, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.lines = queue.Queue()
        threading.Thread(target=self._read_stdout, args=(self.proc, self.lines), daemon=True).start()
        threading.Thread(target=self._read_stderr, args=(self.proc,), daemon=True).start()

    def _read_stdout(self, proc: subprocess.Popen[bytes], lines: queue.Queue[Any]) -> None:
        for raw in proc.stdout:
            try:
                line = raw.decode("utf-8")
            except UnicodeDecodeError:
                line = "<<invalid UTF-8: " + repr(raw) + ">>"
            if line.endswith("\r\n"):
                line = line[:-2] + "<<CRLF: lines must end with LF only>>"
            elif line.endswith("\n"):
                line = line[:-1]
            else:
                line += "<<no line ending>>"
            self.log.add(self.label, "<", line)
            lines.put(line)
        lines.put(EOF)

    def _read_stderr(self, proc: subprocess.Popen[bytes]) -> None:
        for raw in proc.stderr:
            self.log.add(self.label, "!", raw.decode("utf-8", "replace").rstrip("\r\n"))

    def write(self, line: str) -> None:
        self.log.add(self.label, ">", line)
        try:
            self.proc.stdin.write(line.encode("utf-8") + b"\n")
            self.proc.stdin.flush()
        except OSError as e:
            raise StepFailed(f"{self.label}: cannot write to stdin ({e}); did the client exit?")

    def next_line(self, timeout: float) -> str:
        try:
            line = self.lines.get(timeout=timeout)
        except queue.Empty:
            raise StepFailed(f"{self.label}: no output within {timeout:.1f}s") from None
        if line is EOF:
            self.lines.put(EOF)
            raise StepFailed(f"{self.label}: stdout closed (exit status {self.proc.poll()})")
        return line

    def stop(self) -> None:
        """Close stdin; the client must print BYE, print nothing else, and exit 0."""
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        line = self.next_line(LINE_TIMEOUT)
        if line != "BYE":
            raise StepFailed(f"{self.label}: expected BYE at end of input, got {line!r}")
        self.wait_exit()

    def wait_exit(self) -> None:
        try:
            code = self.proc.wait(EXIT_TIMEOUT)
        except subprocess.TimeoutExpired:
            raise StepFailed(f"{self.label}: did not exit within {EXIT_TIMEOUT}s after BYE") from None
        try:
            extra = self.lines.get(timeout=1.0)
        except queue.Empty:
            extra = EOF
        if extra is not EOF:
            raise StepFailed(f"{self.label}: printed {extra!r} after BYE")
        if code != 0:
            raise StepFailed(f"{self.label}: exit status {code}, expected 0")

    def kill(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()


def start_server(log: Transcript, port: int = 0) -> tuple[subprocess.Popen[str], str]:
    proc = subprocess.Popen([sys.executable, str(SERVER), "--port", str(port), "--verbose"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            encoding="utf-8")
    line = proc.stdout.readline().strip()
    if not line.startswith("LISTENING port="):
        proc.kill()
        raise RuntimeError(f"server did not start: {line!r} {proc.stderr.read()}")

    def drain() -> None:
        for l in proc.stderr:
            log.add("server", "~", l.rstrip("\n").split(" server ", 1)[-1])
    threading.Thread(target=drain, daemon=True).start()
    return proc, f"ws://127.0.0.1:{line.split('=')[1]}"


# ---- patterns ---------------------------------------------------------------------------

VAR = re.compile(r"\{\{|\}\}|\{([A-Za-z_][A-Za-z0-9_]*)\}")


def match(pattern: str, line: str, bound: dict[str, str]) -> dict[str, str] | None:
    """Match a whole line; return the new bindings, or None."""
    regex, pos, fresh = [], 0, []
    for m in VAR.finditer(pattern):
        regex.append(re.escape(pattern[pos:m.start()]))
        pos = m.end()
        if m.group(0) in ("{{", "}}"):
            regex.append(re.escape(m.group(0)[0]))
        elif (name := m.group(1)) in bound:
            regex.append(re.escape(bound[name]))
        elif name in fresh:
            regex.append(f"(?P={name})")
        else:
            fresh.append(name)
            regex.append(rf"(?P<{name}>\S+)")
    regex.append(re.escape(pattern[pos:]))
    m = re.fullmatch("".join(regex), line)
    return None if m is None else {**bound, **m.groupdict()}


# ---- scenarios --------------------------------------------------------------------------

@dataclass
class Result:
    scenario: str
    pair: str
    ok: bool
    error: str = ""
    step: int = 0
    transcript: list[str] = field(default_factory=list)


def load_scenarios(only: list[str] | None) -> list[dict[str, Any]]:
    scenarios = []
    for path in sorted(SCENARIOS.glob("*.yaml")):
        s = yaml.safe_load(path.read_text(encoding="utf-8"))
        s.setdefault("name", path.stem)
        if not only or s["name"] in only:
            scenarios.append(s)
    if only and len(scenarios) != len(set(only)):
        raise SystemExit(f"unknown scenario in {only}")
    return scenarios


def run_scenario(s: dict[str, Any], pair: tuple[Platform, Platform]) -> Result:
    label = f"{pair[0].short}-{pair[1].short}"
    log = Transcript()
    server = Server(log)
    data = Path(tempfile.mkdtemp(prefix=f"{s['name']}-{label}-", dir=_tmp_root()))
    clients: dict[str, Client] = {}
    step_no = 0
    try:
        for i, role in enumerate(s["clients"]):
            clients[role] = Client(role, pair[i % 2], server.url, log, data / role)
        bound: dict[str, str] = {}
        for step_no, step in enumerate(s["steps"], 1):
            run_step(step, clients, bound, server)
        step_no = len(s["steps"]) + 1  # the implicit /quit step
        for c in clients.values():
            c.write("/quit")
            line = c.next_line(LINE_TIMEOUT)
            if line != "BYE":
                raise StepFailed(f"{c.label}: expected BYE after /quit, got {line!r}")
            c.wait_exit()
        return Result(s["name"], label, True)
    except StepFailed as e:
        return Result(s["name"], label, False, str(e), step_no, log.events)
    finally:
        for c in clients.values():
            c.kill()
        server.stop()
        shutil.rmtree(data, ignore_errors=True)


class Server:
    """The server under test. `server: stop` / `server: start` simulate an outage; a restarted
    server listens on the same port and, being in-memory, starts empty."""

    def __init__(self, log: Transcript):
        self.log = log
        self.proc, self.url = start_server(log)
        self.port = int(self.url.rsplit(":", 1)[1])

    def stop(self) -> None:
        if self.proc is not None:
            self.log.add("server", "##", "stop")
            self.proc.kill()
            self.proc.wait()
            self.proc = None

    def start(self) -> None:
        if self.proc is None:
            self.log.add("server", "##", f"start on port {self.port}")
            self.proc, _ = start_server(self.log, self.port)


def _tmp_root() -> Path:
    root = RUNS / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root


def run_step(step: dict[str, Any], clients: dict[str, Client], bound: dict[str, str],
             server: Server) -> None:
    if len(step) != 1:
        raise StepFailed(f"a step must have exactly one key: {step}")
    (key, value), = step.items()
    if key == "restart":
        clients[value].stop()
        clients[value].start()
        return
    if key == "crash":
        clients[value].log.add(clients[value].label, "##", "crash (kill)")
        clients[value].kill()
        clients[value].start()
        return
    if key == "server":
        if value not in ("stop", "start"):
            raise StepFailed(f"server step must be stop or start, got {value!r}")
        server.stop() if value == "stop" else server.start()
        return
    role, _, op = key.partition("?")
    if role not in clients:
        raise StepFailed(f"unknown client '{role}' in step {step}")
    c = clients[role]
    if key == role:
        c.write(str(value))
    elif op == "":
        line = c.next_line(LINE_TIMEOUT)
        new = match(str(value), line, bound)
        if new is None:
            raise StepFailed(f"{c.label}: expected  {value}\n{' ' * len(c.label)}  got       {line}")
        bound.update(new)
    elif op == "any":
        lines = [c.next_line(LINE_TIMEOUT) for _ in value]
        for order in itertools.permutations(lines):
            b = dict(bound)
            for pattern, line in zip(value, order):
                b = match(str(pattern), line, b)
                if b is None:
                    break
            if b is not None:
                bound.update(b)
                return
        raise StepFailed(f"{c.label}: lines {lines} do not match {value} in any order")
    elif op == "none":
        try:
            line = c.lines.get(timeout=int(value) / 1000)
        except queue.Empty:
            return
        raise StepFailed(f"{c.label}: expected no output, got {'end of output' if line is EOF else repr(line)}")
    else:
        raise StepFailed(f"unknown step '{key}'")


# ---- main -------------------------------------------------------------------------------

def write_report(results: list[Result]) -> Path:
    RUNS.mkdir(parents=True, exist_ok=True)
    path = RUNS / "report.md"
    failed = [r for r in results if not r.ok]
    out = [f"# Conformance report\n\n{len(results) - len(failed)}/{len(results)} runs passed.\n"]
    out += [f"- {'PASS' if r.ok else 'FAIL'} `{r.scenario}` [{r.pair}]" for r in results]
    for r in failed:
        out += [f"\n## FAIL `{r.scenario}` [{r.pair}], step {r.step}\n", "```", r.error, "```",
                "\nTranscript (`>` stdin, `<` stdout, `!` stderr, `~` server log):\n", "```",
                *r.transcript, "```"]
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description="Run conformance scenarios against built clients")
    ap.add_argument("--pair", help="e.g. py-ts; default: every pairing of built clients")
    ap.add_argument("--platform", help="run only this platform against itself")
    ap.add_argument("--scenario", action="append", help="scenario name (repeatable)")
    args = ap.parse_args()

    platforms = load_platforms()
    if args.platform:
        p, = resolve(args.platform, platforms)
        pairs = [(p, p)]
    elif args.pair:
        a, b = resolve(args.pair.split("-"), platforms)
        pairs = [(a, b)]
    else:
        built = [p for p in platforms.values() if p.exists()]
        missing = [p.name for p in platforms.values() if not p.exists()]
        if missing:
            print(f"skipping platforms with no client: {', '.join(missing)}")
        pairs = list(itertools.product(built, repeat=2))
    for a, b in pairs:
        for p in (a, b):
            if not p.exists():
                raise SystemExit(f"no client at {p.dir}; generate and build it first")
    if not pairs:
        raise SystemExit("no built clients")

    results = []
    for s in load_scenarios(args.scenario):
        for pair in pairs:
            r = run_scenario(s, pair)
            print(f"{'PASS' if r.ok else 'FAIL'}  {r.scenario:<28} [{r.pair}]"
                  + ("" if r.ok else f"  step {r.step}: {r.error.splitlines()[0]}"), flush=True)
            results.append(r)
    report = write_report(results)
    failed = sum(not r.ok for r in results)
    print(f"\n{len(results) - failed}/{len(results)} passed. Report: {report.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
