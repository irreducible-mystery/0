"""The one constraint, checked mechanically: the trail is append-only.

    python3 tools/check.py --base origin/main --head HEAD [--json]

Compares the two refs from their merge base and fails if any file under entries/ was
modified, deleted or renamed, or if an added entry is malformed. Every other file may
change freely (TRAIL.md included; it is regenerated on main anyway).

Prints a JSON object with "ok", "entries_only" and "problems" when --json is given, so
the reflex can read it; otherwise plain lines. Exit 0 when ok, 1 when not, 2 on error.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

from entry import HEADING_RE, NAME_RE, ROOT


def git(*args: str, cwd: pathlib.Path = ROOT) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def changes(base: str, head: str, cwd: pathlib.Path = ROOT) -> list[tuple[str, str, str | None]]:
    """[(status, path, new_path_if_renamed)] between merge-base(base, head) and head."""
    mb = git("merge-base", base, head, cwd=cwd).strip()
    out = []
    # Without -z Git quotes unusual filenames, hiding the entries/ prefix.
    # Decode paths as filesystem names, preserving undecodable bytes and CR/LF.
    raw = subprocess.run(
        ["git", "diff", "--name-status", "--find-renames", "-z", mb, head],
        cwd=cwd, check=True, capture_output=True,
    ).stdout
    fields = iter(os.fsdecode(raw).split("\0")[:-1])
    for value in fields:
        status = value[0]
        path = next(fields)
        new = next(fields) if status in {"R", "C"} else None
        out.append((status, path, new))
    return out


def valid_entry_text(text: str) -> bool:
    first, _, rest = text.partition("\n")
    return bool(HEADING_RE.match(first)) and text.count("\n### ") == 0 and bool(rest.strip())


def historical_blobs(base: str, path: str, cwd: pathlib.Path) -> set[str]:
    """Blob ids this path has had in base's history: what a restoration may restore to."""
    out = set()
    for commit in git("rev-list", base, "--", path, cwd=cwd).split():
        try:
            out.add(git("rev-parse", f"{commit}:{path}", cwd=cwd).strip())
        except subprocess.CalledProcessError:
            pass
    return out


def has_valid_entry_history(base: str, path: str, cwd: pathlib.Path) -> bool:
    """A damaged current version does not make an earlier valid entry disposable."""
    if not NAME_RE.match(path.split("/", 1)[1]):
        return False
    for blob in historical_blobs(base, path, cwd):
        try:
            text = git("cat-file", "blob", blob, cwd=cwd)
        except UnicodeDecodeError:
            continue  # non-UTF-8 damage is not a valid entry version
        if valid_entry_text(text):
            return True
    return False


def evaluate(base: str, head: str, cwd: pathlib.Path = ROOT) -> dict:
    problems: list[str] = []
    entry_adds = 0
    other = 0
    restored = 0
    for status, path, new in changes(base, head, cwd):
        touched = [p for p in (path, new) if p]
        in_entries = any(p.startswith("entries/") and p != "entries/README.md" for p in touched)
        if not in_entries:
            other += 1
            continue
        if status == "M":
            # a change back to what the file once was is a restoration, not an edit
            new_blob = git("rev-parse", f"{head}:{path}", cwd=cwd).strip()
            if new_blob in historical_blobs(base, path, cwd):
                restored += 1
                continue
        if status == "D":
            # removing something that never was a valid entry is tidying, not loss
            if not has_valid_entry_history(base, path, cwd):
                restored += 1
                continue
        if status != "A":
            what = {"M": "modified", "D": "deleted", "R": f"renamed to {new}", "C": "copied", "T": "type-changed"}.get(status, status)
            problems.append(f"{path}: {what}. Entries are never changed; add a new one beside it.")
            continue
        name = path.split("/", 1)[1]
        if "/" in name:
            problems.append(f"{path}: entries live directly in entries/, not in subfolders")
            continue
        if not NAME_RE.match(name):
            problems.append(f"{path}: filename must be YYYYMMDD-HHMMSS-name.md (use tools/entry.py)")
            continue
        try:
            text = git("show", f"{head}:{path}", cwd=cwd)
        except subprocess.CalledProcessError:
            problems.append(f"{path}: cannot read at {head}")
            continue
        first = text.split("\n", 1)[0]
        if not HEADING_RE.match(first):
            problems.append(f"{path}: first line must be '### YYYY-MM-DD HH:MM UTC · name · kind'")
        elif text.count("\n### ") > 0:
            problems.append(f"{path}: one heading per entry file")
        elif not text.split("\n", 1)[1].strip():
            problems.append(f"{path}: empty body")
        entry_adds += 1
    return {
        "ok": not problems,
        "entries_added": entry_adds,
        "entries_restored": restored,
        "other_changes": other,
        "entries_only": not problems and entry_adds > 0 and other == 0 and restored == 0,
        "problems": problems,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        result = evaluate(args.base, args.head)
    except subprocess.CalledProcessError as e:
        print(f"check: git failed: {e.stderr.strip()}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result))
    else:
        for p in result["problems"]:
            print("  " + p)
        print(
            ("ok" if result["ok"] else "NOT OK")
            + f": {result['entries_added']} entries added, {result['other_changes']} other files changed"
            + (", entries only" if result["entries_only"] else "")
        )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
