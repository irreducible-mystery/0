"""Run the repository's local checks without invoking either live reflex.

    python3 tools/verify.py [--base origin/main] [--head HEAD]

Runs the tools suite, each present project's documented checker, and the generated
trail comparison. --base also checks the append-only diff. Reports every failure
instead of stopping at the first. Standard library only; no network or writes
outside the scratch repositories made by tests.
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
# Explicit commands: never guess that an arbitrary script is safe to execute.
PROJECTS = (
    ("jumps", "jumps/jumps.py", ()),
    ("observers", "observers/observers.py", ()),
    ("field", "field/field.py", ("--check",)),
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="also check the append-only diff from this ref")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args(argv)
    commands = [("tools", ("-I", "-m", "unittest", "discover", "-s", "tools", "-p", "test_*.py"))]
    for name, path, extra in PROJECTS:
        if (ROOT / name).exists():
            commands.append((name, ("-I", path, *extra)))
        else:
            print(f"SKIP {name}: not present in this checkout", flush=True)
    commands.append(("trail", ("tools/assemble.py", "--check")))
    if args.base:
        commands.append(("append-only", ("tools/check.py", "--base", args.base, "--head", args.head)))
    failed = []
    for name, command in commands:
        print(f"\n=== {name} ===", flush=True)
        try:
            result = subprocess.run([sys.executable, "-B", *command], cwd=ROOT, timeout=600)
            code = result.returncode
        except (OSError, subprocess.TimeoutExpired) as error:
            print(f"FAIL {name}: {error}", flush=True)
            code = 1
        if code:
            failed.append(name)
        print(f"{'FAIL' if code else 'PASS'} {name}", flush=True)
    print(f"\n{len(commands)} checks run; {len(failed)} failed" +
          (f": {', '.join(failed)}" if failed else ""), flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
