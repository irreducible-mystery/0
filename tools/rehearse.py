"""Rehearse the consolidate reflex on a scratch remote. Nothing here touches GitHub.

    python3 tools/rehearse.py [--tools DIR] [--only SCENARIO ...]

Each scenario gets a bare remote holding a small trail, as main would: entries, a TRAIL.md that
is current, and the bot's commit that ended the last consolidation. It then lands a change on
that remote's main the way a writer would (a direct push, or a merge as the reflex makes one),
runs consolidate.py from DIR in a clone of the remote after each landing, and reports what main
holds afterwards. A stub `gh` is first on PATH and records that consolidate would have posted
something; nothing is posted. Variables for GitHub are removed from the environment first. DIR
defaults to the tools/ this file is in; point it at another branch's tools/ to see what that
branch's consolidate would do.

The scratch copy carries the tools and a stub test, not the real suite: the scenarios are about
what consolidate does with the trail and with a red test, and the suite would only repeat itself.

Scenarios:
  revert_commit          one commit pushed directly, changing an entry. Consolidate should revert it.
  revert_merge           a branch of two commits, one changing an entry, merged as the reflex merges
                         a pull request. Consolidate should revert the merge.
  revert_merge_two_edits a branch of two commits that both change the same entry, merged the same
                         way. Consolidate should revert the merge, and leave main as it was.
  red_tests              a merge that adds a failing test. Consolidate should revert it.
  whole_push             two commits pushed together: the entry change, then a benign commit on top.
  lost_race              the revert's push loses a race: another writer pushes first, once.
                         Consolidate runs a second time afterwards, as the next landing would.
  collateral             a benign change is accepted; later a tampered entry is pushed. Shows what
                         a revert takes with it: does the earlier, accepted change stay?
"""
from __future__ import annotations

import argparse
import dataclasses
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SCENARIOS = ("revert_commit", "revert_merge", "revert_merge_two_edits", "red_tests",
             "whole_push", "lost_race", "collateral")
MARK = "tampered by the rehearsal"
TAMPER = MARK + ": text a writer pushed directly\n"
WRITER = {"user.name": "writer", "user.email": "writer@rehearsal.invalid"}
BOT = {"user.name": "github-actions[bot]", "user.email": "41898282+github-actions[bot]@users.noreply.github.com"}
STUB_TEST = "import unittest\n\n\nclass Stub(unittest.TestCase):\n    def test_stub(self):\n        self.assertTrue(True)\n"
RED_TEST = "import unittest\n\n\nclass Red(unittest.TestCase):\n    def test_red(self):\n        self.fail('rehearsal: a red test')\n"
GH_STUB = '#!/bin/sh\n# rehearsal only: record that a call was made, post nothing\necho rehearse-gh-call >> "$REHEARSE_GH_LOG"\nexit 0\n'
GIT_WRAPPER = """#!/bin/sh
# rehearsal only: when consolidate is about to push, another writer pushes first, once
if [ "$1" = push ] && [ -n "$REHEARSE_RACE_FLAG" ] && [ -e "$REHEARSE_RACE_FLAG" ]; then
    rm -f "$REHEARSE_RACE_FLAG"
    "$REHEARSE_REAL_GIT" -C "$REHEARSE_RACE_CLONE" pull -q --ff-only origin main
    "$REHEARSE_REAL_GIT" -C "$REHEARSE_RACE_CLONE" commit -q --allow-empty -m "another writer lands first"
    "$REHEARSE_REAL_GIT" -C "$REHEARSE_RACE_CLONE" push -q origin HEAD:main
fi
exec "$REHEARSE_REAL_GIT" "$@"
"""


@dataclasses.dataclass
class Outcome:
    scenario: str
    verdict: str                   # "reverted": the landed change is gone from main; "kept": still there
    exit_codes: list[int]          # one per consolidate run
    main_log: list[str]            # newest first
    messages: list[str]            # what consolidate printed that matters
    gh_calls: int                  # calls to the stub gh; none were sent
    race_fired: bool | None        # lost_race only: whether the other writer's push happened
    differs_from_before: list[str] | None  # reverted only: files that differ from before the landing


def git(cwd: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def configure(path: pathlib.Path, identity: dict[str, str]) -> None:
    for key, value in identity.items():
        git(path, "config", key, value)


def clean_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith(("GH_", "GITHUB_", "ACTIONS_"))}


def build(d: pathlib.Path, tools: pathlib.Path) -> None:
    """A bare remote whose main is a seed trail, and three clones: work runs consolidate as the
    bot does; land and other are writers."""
    remote = d / "remote.git"
    git(d, "init", "-q", "--bare", str(remote))
    git(remote, "symbolic-ref", "HEAD", "refs/heads/main")
    seed = d / "seed"
    git(d, "init", "-q", "-b", "main", str(seed))
    configure(seed, WRITER)
    (seed / "tools").mkdir()
    for path in tools.glob("*.py"):
        if not path.name.startswith("test_"):
            shutil.copy(path, seed / "tools" / path.name)
    (seed / "tools" / "test_seed.py").write_text(STUB_TEST)
    shutil.copytree(tools.parent / "entries", seed / "entries")
    subprocess.run([sys.executable, "tools/assemble.py"], cwd=seed, check=True, capture_output=True)
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", "seed")
    # the consolidation that ended the last landing, as the bot leaves it: a real trail has many
    bot_args = [arg for key, value in BOT.items() for arg in ("-c", f"{key}={value}")]
    git(seed, *bot_args, "commit", "-q", "--allow-empty", "-m", "trail: 1 entries")
    git(seed, "push", "-q", str(remote), "HEAD:main")
    for name, identity in (("work", BOT), ("land", WRITER), ("other", WRITER)):
        git(d, "clone", "-q", str(remote), str(d / name))
        configure(d / name, identity)


def first_entry(work: pathlib.Path) -> str:
    return sorted(p.name for p in (work / "entries").glob("*.md"))[0]


def tamper(clone: pathlib.Path, entry: str) -> None:
    path = clone / "entries" / entry
    path.write_text(path.read_text() + TAMPER)


def land(name: str, land_dir: pathlib.Path, entry: str, part: int = 0) -> None:
    if name == "collateral":
        if part == 1:
            (land_dir / "accepted.txt").write_text("an accepted change\n")
            git(land_dir, "add", "-A")
            git(land_dir, "commit", "-q", "-m", "an accepted change")
            git(land_dir, "push", "-q", "origin", "HEAD:main")
        else:
            tamper(land_dir, entry)
            git(land_dir, "commit", "-q", "-am", "tamper")
            git(land_dir, "push", "-q", "origin", "HEAD:main")
    elif name in ("revert_commit", "lost_race"):
        tamper(land_dir, entry)
        git(land_dir, "commit", "-q", "-am", "tamper")
        git(land_dir, "push", "-q", "origin", "HEAD:main")
    elif name == "revert_merge":
        git(land_dir, "checkout", "-q", "-b", "topic")
        (land_dir / "notes.txt").write_text("a benign step\n")
        git(land_dir, "add", "-A")
        git(land_dir, "commit", "-q", "-m", "first step")
        tamper(land_dir, entry)
        git(land_dir, "commit", "-q", "-am", "tamper")
        git(land_dir, "checkout", "-q", "main")
        git(land_dir, "merge", "-q", "--no-ff", "-m", "merge #99: tamper", "topic")
        git(land_dir, "push", "-q", "origin", "HEAD:main")
    elif name == "revert_merge_two_edits":
        git(land_dir, "checkout", "-q", "-b", "topic")
        tamper(land_dir, entry)
        git(land_dir, "commit", "-q", "-am", "tamper")
        tamper(land_dir, entry)
        git(land_dir, "commit", "-q", "-am", "tamper again")
        git(land_dir, "checkout", "-q", "main")
        git(land_dir, "merge", "-q", "--no-ff", "-m", "merge #97: two edits to an entry", "topic")
        git(land_dir, "push", "-q", "origin", "HEAD:main")
    elif name == "red_tests":
        git(land_dir, "checkout", "-q", "-b", "topic")
        (land_dir / "tools" / "test_seed_red.py").write_text(RED_TEST)
        git(land_dir, "add", "-A")
        git(land_dir, "commit", "-q", "-m", "a red test")
        git(land_dir, "checkout", "-q", "main")
        git(land_dir, "merge", "-q", "--no-ff", "-m", "merge #98: a red test", "topic")
        git(land_dir, "push", "-q", "origin", "HEAD:main")
    elif name == "whole_push":
        tamper(land_dir, entry)
        git(land_dir, "commit", "-q", "-am", "tamper")
        (land_dir / "notes.txt").write_text("a benign step\n")
        git(land_dir, "add", "-A")
        git(land_dir, "commit", "-q", "-m", "benign step on top")
        git(land_dir, "push", "-q", "origin", "HEAD:main")


def landed(name: str, remote: pathlib.Path, entry: str) -> bool:
    if name == "red_tests":
        return bool(git(remote, "ls-tree", "--name-only", "main", "--", "tools/test_seed_red.py"))
    return MARK in git(remote, "show", f"main:entries/{entry}")


def run(name: str, tools: pathlib.Path = HERE) -> Outcome:
    if name not in SCENARIOS:
        raise ValueError(f"no scenario {name!r}; choose from {', '.join(SCENARIOS)}")
    if not (tools / "consolidate.py").exists():
        raise FileNotFoundError(f"{tools / 'consolidate.py'} does not exist")
    real_git = shutil.which("git")
    with tempfile.TemporaryDirectory(prefix=f"rehearse-{name}-") as tmp:
        d = pathlib.Path(tmp)
        build(d, tools)
        remote, work, land_dir, other = d / "remote.git", d / "work", d / "land", d / "other"
        entry = first_entry(work)

        bin_dir = d / "bin"
        bin_dir.mkdir()
        for stub, text in (("gh", GH_STUB), ("git", GIT_WRAPPER)):
            (bin_dir / stub).write_text(text)
            (bin_dir / stub).chmod(0o755)
        gh_log, flag = d / "gh.log", d / "race.flag"
        env = clean_env()
        env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
        env.update(REHEARSE_GH_LOG=str(gh_log), REHEARSE_REAL_GIT=real_git,
                   REHEARSE_RACE_CLONE=str(other), REHEARSE_RACE_FLAG=str(flag))

        exit_codes, messages = [], []

        def consolidate() -> None:
            r = subprocess.run([sys.executable, "tools/consolidate.py"], cwd=work, env=env,
                               capture_output=True, text=True)
            exit_codes.append(r.returncode)
            messages.extend(line for line in (r.stdout + r.stderr).splitlines()
                            if line.startswith(("consolidate", "fatal", "FAILED", "reflex")))

        if name == "collateral":
            land(name, land_dir, entry, part=1)
            consolidate()
            before = git(remote, "rev-parse", "main")
            land(name, land_dir, entry, part=2)
        else:
            before = git(remote, "rev-parse", "main")
            land(name, land_dir, entry)
        if name == "lost_race":
            flag.write_text("")
        consolidate()
        if name == "lost_race":
            consolidate()

        still = landed(name, remote, entry)
        return Outcome(
            scenario=name,
            verdict="kept" if still else "reverted",
            exit_codes=exit_codes,
            main_log=git(remote, "log", "--format=%s", "-n", "6", "main").splitlines(),
            messages=messages,
            gh_calls=gh_log.read_text().splitlines().count("rehearse-gh-call") if gh_log.exists() else 0,
            race_fired=(not flag.exists()) if name == "lost_race" else None,
            differs_from_before=None if still else git(remote, "diff", "--name-only", before, "main").splitlines(),
        )


def report(o: Outcome) -> str:
    head = f"{o.scenario}: {o.verdict}   consolidate exit codes {o.exit_codes}, gh calls recorded (none sent) {o.gh_calls}"
    if o.race_fired is not None:
        head += f", other writer's push fired: {o.race_fired}"
    lines = [head, "    main, newest first: " + "  <-  ".join(o.main_log)]
    if o.differs_from_before:
        lines.append("    files that differ from before the landing: " + ", ".join(o.differs_from_before))
    lines += ["    " + m for m in o.messages]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tools", type=pathlib.Path, default=HERE,
                    help="the tools/ directory whose consolidate.py is rehearsed (default: this one)")
    ap.add_argument("--only", nargs="+", choices=SCENARIOS, default=list(SCENARIOS), metavar="SCENARIO")
    args = ap.parse_args(argv)
    tools = args.tools.resolve()
    print(f"rehearsing {tools / 'consolidate.py'} on scratch remotes; nothing is posted or pushed to GitHub")
    for name in args.only:
        print(report(run(name, tools)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
