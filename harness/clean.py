"""Delete generated client folders.

    python harness/clean.py <python|typescript|all>
"""

from __future__ import annotations

import os
import shutil
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from harness.platforms import Platform, resolve  # noqa: E402

CLIENTS = ROOT / "clients"


def clean(p: Platform) -> None:
    target = p.dir.resolve()
    if CLIENTS.resolve() not in target.parents:
        raise SystemExit(f"refusing to delete {target}: not inside {CLIENTS}")
    if target.exists():
        def make_writable(func, path, _exc):  # read-only files on Windows
            os.chmod(path, stat.S_IWRITE)
            func(path)
        shutil.rmtree(target, onexc=make_writable)
    print(f"clean  {p.name}: removed {target.relative_to(ROOT)}")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    for p in resolve(sys.argv[1]):
        clean(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
