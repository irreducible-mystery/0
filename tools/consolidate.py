"""Consolidate main after something lands on it: keep what held up, undo what did not.

    python3 tools/consolidate.py

Looks at what the push onto origin/main added. If the range changed the trail in a way the
trail does not allow, or the tests fail on it, the whole range is reverted as one new commit
(history is kept) and the pull request it came from, if any, gets a comment saying why.
Otherwise TRAIL.md is regenerated from entries/ and committed if it changed. Its own commits
are skipped, so it cannot loop.

A direct push can carry several commits; checking only the newest would let a tamper in an
earlier commit of the same push survive, because the newest commit alone can be clean. The
range starts at GitHub's `before` when the workflow passes it (BEFORE_SHA), else at the
newest commit's first parent, which is the right base for a merge the reflex just made.
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check  # noqa: E402

ROOT = check.ROOT
BOT = "github-actions[bot]"


def sh(*args: str, check_=True, cwd: pathlib.Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, check=check_, capture_output=True, text=True)


def push_base(head: str, parents: list[str], cwd: pathlib.Path = ROOT) -> str | None:
    """The commit this landing started from.

    GitHub's `before` is exact when the workflow passes it (BEFORE_SHA). When it is absent or
    is not an ancestor, the base is the newest consolidation commit on main's first-parent
    chain: `trail:` or `Revert`, authored by the bot. That is where the last landing ended, so
    every commit a direct push added sits after it. A hand-pusher who forges the bot's author
    name and subject could move that marker into their own push; the README already says that
    whoever can push to main by hand can shape its history. Passing BEFORE_SHA closes that too.
    """
    before = os.environ.get("BEFORE_SHA", "").strip()
    if before and set(before) != {"0"}:
        if sh("git", "merge-base", "--is-ancestor", before, head, check_=False, cwd=cwd).returncode == 0:
            return before
    marker = last_consolidation(head, cwd)
    if marker:
        return marker
    return parents[0] if parents else None


def last_consolidation(head: str, cwd: pathlib.Path = ROOT) -> str | None:
    """The newest commit before head that is a consolidation: bot-authored, `trail:` or `Revert`."""
    for commit in sh("git", "rev-list", "--first-parent", head, cwd=cwd).stdout.split()[1:]:
        author = sh("git", "log", "-1", "--format=%an", commit, cwd=cwd).stdout.strip()
        subject = sh("git", "log", "-1", "--format=%s", commit, cwd=cwd).stdout.strip()
        if author == BOT and (subject.startswith("trail:") or subject.startswith("Revert")):
            return commit
    return None


def revert_range(base: str | None, head: str, cwd: pathlib.Path = ROOT) -> tuple[bool, str]:
    """Revert every commit in base..head as one new commit, newest first. Returns (ok, error).

    Reverting only the newest commit would leave an earlier commit of the same push in place,
    which is the whole point of checking the range. On any conflict the sequence is aborted and
    the tree is left as it was, so the caller can open an issue instead of pushing a half-revert.
    """
    if base:
        commits = sh("git", "rev-list", "--reverse", f"{base}..{head}", cwd=cwd).stdout.split()
    else:
        commits = [head]
    for commit in reversed(commits):
        parent_count = len(sh("git", "rev-list", "--parents", "-n", "1", commit, cwd=cwd).stdout.split()) - 1
        args = ["git", "revert", "--no-commit"] + (["-m", "1"] if parent_count > 1 else []) + [commit]
        r = sh(*args, check_=False, cwd=cwd)
        if r.returncode != 0:
            sh("git", "revert", "--abort", check_=False, cwd=cwd)
            return False, (r.stderr or r.stdout)[-1500:]
    sh("git", "revert", "--quit", check_=False, cwd=cwd)
    if sh("git", "diff", "--cached", "--quiet", check_=False, cwd=cwd).returncode == 0:
        return True, ""  # every commit in the range was already a no-op
    subject = f"Revert the push {base[:7]}..{head[:7]}" if base else f"Revert {head[:7]}"
    r = sh("git", "commit", "-q", "-m", subject, check_=False, cwd=cwd)
    if r.returncode != 0:
        return False, (r.stderr or r.stdout)[-1500:]
    return True, ""


def push_main() -> bool:
    for _ in range(2):
        r = sh("git", "push", "origin", "HEAD:main", check_=False)
        if r.returncode == 0:
            return True
        print(f"consolidate: push rejected: {r.stderr.strip()[-300:]}")
        sh("git", "fetch", "-q", "origin", "main")
        # someone else pushed first: our commit is a revert or a regeneration, both of which are
        # cheap to redo, so drop ours and let the next run (or the caller) start over
        return False
    return False


def comment_on_pr(subject: str, text: str) -> None:
    m = re.search(r"#(\d+)", subject)
    if not m:
        return
    sh("gh", "api", "-X", "POST", f"repos/{{owner}}/{{repo}}/issues/{m.group(1)}/comments", "-f", f"body={text}", check_=False)


def main(argv=None) -> int:
    sh("git", "fetch", "-q", "origin", "main")
    sh("git", "checkout", "-q", "--detach", "origin/main")
    head = sh("git", "rev-parse", "HEAD").stdout.strip()
    subject = sh("git", "log", "-1", "--format=%s").stdout.strip()
    author = sh("git", "log", "-1", "--format=%an").stdout.strip()
    parents = sh("git", "log", "-1", "--format=%P").stdout.split()
    if author == BOT and subject.startswith("trail:"):
        print("consolidate: newest commit is my own regeneration; nothing to do")
        return 0
    if author == BOT and subject.startswith("Revert"):
        print("consolidate: newest commit is my own revert; nothing to do")
        return 0

    problems: list[str] = []
    base = push_base(head, parents)
    if base:
        result = check.evaluate(base, head)
        problems += result["problems"]
    t = subprocess.run([sys.executable, "-I", "-m", "unittest", "discover", "-s", "tools", "-p", "test_*.py"],
                       cwd=ROOT, capture_output=True, text=True, timeout=600)
    if t.returncode != 0:
        problems.append("tests fail on main:\n```\n" + (t.stderr or t.stdout)[-2000:] + "\n```")

    if problems:
        print(f"consolidate: main is red at {head[:7]}; reverting {base[:7] if base else 'it'}")
        ok, err = revert_range(base, head)
        text = "\n".join(f"- {p}" for p in problems)
        if not ok:
            sh("gh", "issue", "create", "--title", f"reflex: main is red at {head[:7]} and could not be reverted",
               "--body", f"`{subject}`\n\n{text}\n\n```\n{err}\n```", check_=False)
            return 1
        if not push_main():
            return 1
        comment_on_pr(subject, f"reflex: after merging, main was red, so the landing "
                      f"(`{base[:7] if base else head[:7]}..{head[:7]}`) was reverted as one new commit; "
                      f"history is kept:\n{text}\n\nFix on the branch and open it again.")
        return 0

    a = subprocess.run([sys.executable, "tools/assemble.py"], cwd=ROOT, capture_output=True, text=True)
    print(a.stdout.strip() or a.stderr.strip())
    if a.returncode != 0:
        return 1
    if not sh("git", "status", "--porcelain", "TRAIL.md").stdout.strip():
        print("consolidate: TRAIL.md already current")
        return 0
    n = sum(1 for p in (ROOT / "entries").iterdir() if p.suffix == ".md" and p.name != "README.md")
    sh("git", "add", "TRAIL.md")
    sh("git", "commit", "-q", "-m", f"trail: {n} entries")
    return 0 if push_main() else 1


if __name__ == "__main__":
    sys.exit(main())
