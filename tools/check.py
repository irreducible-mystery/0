"""The one constraint, checked mechanically: the trail is append-only.

    python3 tools/check.py --base origin/main --head HEAD [--json]

Compares the two refs from their merge base and fails if any file under entries/ was
modified, deleted or renamed, or if an added entry is malformed. Every other file may
change freely (TRAIL.md included; it is regenerated on main anyway).

Two changes under entries/ are allowed without being additions, and neither counts as
"entries only": putting an entry back to the first well-formed text it had on main's own line
of history is a restoration, not an edit; removing a file that never held a well-formed entry
is tidying, not a loss.

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
    # decoded as UTF-8 whatever the locale says, so a verdict does not depend on the environment
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, encoding="utf-8").stdout


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


def original_blob(base: str, path: str, cwd: pathlib.Path) -> str | None:
    """The blob id of the first well-formed version of this path on base's own line of history
    since the path last appeared: the text the trail first showed under this name. A restoration
    restores to this and to nothing else, so a tamper that once landed on main and was reverted
    cannot be put back as one.

    Only the first-parent chain is read: the commits of a merged branch are not the trail, so a
    draft pushed before the merge, or a version planted in a pull request's own history, is not
    an original. A deletion on the chain starts the path afresh, so a landing that was reverted
    before the trail ever showed it is not an original either. Versions that are not well-formed
    entries (junk, bytes that are not UTF-8) are passed over; a path with no such version, or
    whose name is not an entry name, has no original and cannot be restored. Whoever can push to
    main by hand can still shape its first-parent chain; no reading of history resists the one
    who writes it."""
    if not NAME_RE.match(path.split("/", 1)[1]):
        return None
    original = None
    for commit in git("rev-list", "--first-parent", "--reverse", base, "--", path, cwd=cwd).split():
        try:
            blob = git("rev-parse", f"{commit}:{path}", cwd=cwd).strip()
        except subprocess.CalledProcessError:
            original = None  # the path is absent here: what comes after starts afresh
            continue
        if original is not None:
            continue
        try:
            text = git("cat-file", "blob", blob, cwd=cwd)
        except (subprocess.CalledProcessError, UnicodeDecodeError):
            continue  # not a file, or bytes that are not UTF-8: not a well-formed entry
        if valid_entry_text(text):
            original = blob
    return original


def historical_blobs(base: str, path: str, cwd: pathlib.Path) -> set[str]:
    """Blob ids this path has had in base's history."""
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
            # back to the first well-formed text the entry had on main: a restoration, not an edit
            new_blob = git("rev-parse", f"{head}:{path}", cwd=cwd).strip()
            original = original_blob(base, path, cwd)
            if new_blob == original:
                restored += 1
                continue
            hint = f"; a restoration would put it back to its first text on main (blob {original[:7]})" if original else ""
            problems.append(f"{path}: modified. Entries are never changed; add a new one beside it{hint}.")
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
        except UnicodeDecodeError:
            problems.append(f"{path}: content must be UTF-8 text")
            continue
        first, _, body = text.partition("\n")
        if not HEADING_RE.match(first):
            problems.append(f"{path}: first line must be '### YYYY-MM-DD HH:MM UTC · name · kind'")
        elif text.count("\n### ") > 0:
            problems.append(f"{path}: one heading per entry file")
        elif not body.strip():
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
            + (f", {result['entries_restored']} restored" if result["entries_restored"] else "")
            + (", entries only" if result["entries_only"] else "")
        )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
