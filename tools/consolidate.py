"""Consolidate main after something lands on it: keep what held up, undo what did not.

    python3 tools/consolidate.py

Looks at the newest commit on origin/main. If it changed the trail in a way the trail does
not allow, or the tests fail on it, that commit is reverted (a new commit; history is kept)
and the pull request it came from, if any, gets a comment saying why. Otherwise TRAIL.md is
regenerated from entries/ and committed if it changed. Its own commits are skipped, so it
cannot loop.
"""
from __future__ import annotations

import base64
import os
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check  # noqa: E402

ROOT = check.ROOT
BOT = "github-actions[bot]"


def sh(*args: str, check_=True) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=ROOT, check=check_, capture_output=True, text=True)


def push_env() -> dict[str, str]:
    """The environment for the one push to main. The checkout keeps no credentials on disk
    (persist-credentials: false), so the workflow's token is handed to this push, as git's
    basic-auth header, through the environment. Without a token (a run on a laptop) the push
    uses whatever git already has."""
    env = dict(os.environ)
    token = env.get("GH_TOKEN", "")
    if token:
        # appended after any git configuration the environment already carries (GIT_CONFIG_COUNT)
        n = int(env.get("GIT_CONFIG_COUNT") or 0)
        basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        env.update({"GIT_CONFIG_COUNT": str(n + 1),
                    f"GIT_CONFIG_KEY_{n}": "http.https://github.com/.extraheader",
                    f"GIT_CONFIG_VALUE_{n}": f"AUTHORIZATION: basic {basic}"})
    return env


def push_main() -> bool:
    for _ in range(2):
        r = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, env=push_env(),
                           capture_output=True, text=True)
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
    if parents:
        result = check.evaluate(parents[0], head)
        problems += result["problems"]
    t = subprocess.run([sys.executable, "-I", "-m", "unittest", "discover", "-s", "tools", "-p", "test_*.py"],
                       cwd=ROOT, capture_output=True, text=True, timeout=600)
    if t.returncode != 0:
        problems.append("tests fail on main:\n```\n" + (t.stderr or t.stdout)[-2000:] + "\n```")

    if problems:
        print(f"consolidate: main is red at {head[:7]}; reverting")
        args = ["git", "revert", "--no-edit"] + (["-m", "1"] if len(parents) > 1 else []) + [head]
        r = sh(*args, check_=False)
        text = "\n".join(f"- {p}" for p in problems)
        if r.returncode != 0:
            sh("git", "revert", "--abort", check_=False)
            sh("gh", "issue", "create", "--title", f"reflex: main is red at {head[:7]} and could not be reverted",
               "--body", f"`{subject}`\n\n{text}\n\n```\n{(r.stderr or r.stdout)[-1500:]}\n```", check_=False)
            return 1
        if not push_main():
            return 1
        comment_on_pr(subject, f"reflex: after merging, main was red, so the merge was reverted "
                      f"(`{head[:7]}` stays in history; the revert is a new commit):\n{text}\n\nFix on the branch and open it again.")
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
