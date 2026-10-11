"""Platform definitions, read from the YAML front matter of spec/platforms/*.md.

A new platform is a new spec/platforms/<name>.md with the same keys; nothing here changes.
"""

from __future__ import annotations

import shlex
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PLATFORM_SPECS = ROOT / "spec" / "platforms"


@dataclass(frozen=True)
class Platform:
    name: str
    short: str
    dir: Path
    spec: Path
    setup: tuple[str, ...]
    build: tuple[str, ...]
    test: tuple[str, ...]
    run: str

    def argv(self, command: str) -> list[str]:
        """Split a command and resolve its program, so `npm` works on Windows too."""
        args = shlex.split(command)
        if args[0] == "python":
            args[0] = sys.executable
        else:
            args[0] = shutil.which(args[0]) or args[0]
        return args

    def exists(self) -> bool:
        return self.dir.is_dir()


def load_platforms() -> dict[str, Platform]:
    platforms: dict[str, Platform] = {}
    for spec in sorted(PLATFORM_SPECS.glob("*.md")):
        text = spec.read_text(encoding="utf-8")
        if not text.startswith("---"):
            raise ValueError(f"{spec}: missing front matter")
        meta = yaml.safe_load(text.split("---", 2)[1])
        p = Platform(
            name=meta["platform"],
            short=meta["short"],
            dir=ROOT / meta["dir"],
            spec=spec,
            setup=tuple(meta.get("setup") or ()),
            build=tuple(meta.get("build") or ()),
            test=tuple(meta.get("test") or ()),
            run=meta["run"],
        )
        if p.name != spec.stem:
            raise ValueError(f"{spec}: platform '{p.name}' must match the file name")
        platforms[p.name] = p
    return platforms


def resolve(names: list[str] | str, platforms: dict[str, Platform] | None = None) -> list[Platform]:
    """Turn 'all', a platform name or a short name into Platform objects."""
    platforms = platforms or load_platforms()
    names = [names] if isinstance(names, str) else names
    if names == ["all"]:
        return list(platforms.values())
    by_short = {p.short: p for p in platforms.values()}
    out = []
    for n in names:
        p = platforms.get(n) or by_short.get(n)
        if p is None:
            raise SystemExit(f"unknown platform '{n}'; known: {', '.join(platforms)}")
        out.append(p)
    return out
