"""The reflexes. Runs in GitHub Actions with `gh` and GH_TOKEN / GH_REPO set; nobody decides.

    python3 tools/reflex.py pr <N>     # look at one pull request and act
    python3 tools/reflex.py all        # look at every open pull request; close the stale ones

What it does with a pull request, in order:

1. Fetch it and merge it onto main in a scratch tree. Conflict -> say so once, stop.
2. Run tools/check.py (the trail is append-only) and the tests on the merged tree.
   Red -> say so once per head commit, stop.
3. If the pull request only adds entries, merge it now. Adding a file cannot break anything.
4. Otherwise count run reports: a comment line `run: ok <sha> by <name>` where <sha> is a
   prefix of the current head and <name> (one word, no spaces) is not the author's name (the author's name is the
   `by:` line of the pull request body, else their login). Distinct names >= dial `quorum`,
   and no `run: fail` on this head -> merge. Else say once per head what it is waiting for.
5. After any merge, consolidate main (tools/consolidate.py): regenerate TRAIL.md, and if
   main is red, revert the merge.

Names are self-reported. That is a trust rule, not a security one; it is cheap because a
wrong merge is one revert away and nothing is ever lost.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check  # noqa: E402
import consolidate  # noqa: E402
import dial  # noqa: E402

ROOT = check.ROOT
REPO = os.environ.get("GH_REPO", "")
REPORT_RE = re.compile(r"^\s*run:\s*(ok|fail)\s+([0-9a-fA-F]{7,40})\s+by\s+(\S+)", re.M)
BY_RE = re.compile(r"^\s*(?:by|session|name)\s*:\s*(.+?)\s*$", re.M | re.I)
MARK = "<!-- reflex {sha} {state} -->"


def sh(*args: str, cwd=ROOT, check_=True, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, check=check_, capture_output=True, text=True, env=env)


def gh(*args: str, cwd=ROOT) -> str:
    return sh("gh", *args, cwd=cwd).stdout


def gh_json(path: str, paginate: bool = False):
    args = ["api", path] + (["--paginate", "--slurp"] if paginate else [])
    data = json.loads(gh(*args))
    if paginate:  # --slurp gives a list of pages
        return [item for page in data for item in page]
    return data


def author_name(pr: dict) -> str:
    m = BY_RE.search(pr.get("body") or "")
    return (m.group(1) if m else pr["user"]["login"]).strip()


def parse_reports(comments: list[dict], head: str) -> dict[str, dict]:
    """name -> {"ok": bool, "login": str} for reports naming this head; a fail wins over an ok."""
    out: dict[str, dict] = {}
    for c in comments:
        for verdict, sha, name in REPORT_RE.findall(c.get("body") or ""):
            if len(sha) < 7 or not head.lower().startswith(sha.lower()):
                continue
            name = name.strip().strip("*_`")
            prev = out.get(name)
            ok = verdict.lower() == "ok" and (prev is None or prev["ok"])
            out[name] = {"ok": ok, "login": c["user"]["login"]}
    return out


def reports(number: int, head: str) -> dict[str, dict]:
    return parse_reports(gh_json(f"repos/{REPO}/issues/{number}/comments?per_page=100", paginate=True), head)


def said_already(number: int, sha: str, state: str) -> bool:
    mark = MARK.format(sha=sha[:12], state=state)
    return any(mark in (c.get("body") or "") for c in gh_json(f"repos/{REPO}/issues/{number}/comments?per_page=100", paginate=True))


def say(number: int, sha: str, state: str, text: str) -> None:
    if said_already(number, sha, state):
        return
    body = f"{text}\n\n{MARK.format(sha=sha[:12], state=state)}"
    try:
        gh("api", "-X", "POST", f"repos/{REPO}/issues/{number}/comments", "-f", f"body={body}")
    except subprocess.CalledProcessError as e:
        print(f"reflex: could not comment on #{number}: {e.stderr.strip()}")


def run_tests_in(tree: pathlib.Path) -> tuple[bool, str]:
    """Run the merged tree's tests in a copy, with no token in the environment."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GH_", "GITHUB_", "ACTIONS_"))}
    env["PATH"] = os.environ.get("PATH", "")
    with tempfile.TemporaryDirectory() as d:
        dst = pathlib.Path(d) / "tree"
        shutil.copytree(tree, dst, ignore=shutil.ignore_patterns(".git"))
        r = subprocess.run([sys.executable, "-I", "-m", "unittest", "discover", "-s", "tools", "-p", "test_*.py"],
                           cwd=dst, capture_output=True, text=True, env=env, timeout=600)
    return r.returncode == 0, (r.stderr or r.stdout)[-3000:]


def look(number: int) -> str:
    pr = gh_json(f"repos/{REPO}/pulls/{number}")
    if pr["state"] != "open":
        return "not open"
    if pr.get("draft"):
        return "draft; left alone"
    title = pr["title"]
    # two fetches on purpose: with two refs in one fetch, FETCH_HEAD is the first of them
    ref = f"refs/reflex/pr-{number}"
    sh("git", "fetch", "-q", "origin", "main")
    sh("git", "fetch", "-q", "origin", f"+refs/pull/{number}/head:{ref}")
    head = sh("git", "rev-parse", ref).stdout.strip()
    if head != pr["head"]["sha"]:
        print(f"reflex: fetched {head[:7]} but the API says the head is {pr['head']['sha'][:7]}; using what I fetched")

    # 1. merge onto main in a scratch tree
    wt = ROOT.parent / f"reflex-wt-{number}"
    sh("git", "worktree", "remove", "--force", str(wt), check_=False)
    sh("git", "worktree", "add", "-q", "--detach", str(wt), "origin/main")
    try:
        m = sh("git", "merge", "--no-ff", "--no-edit", ref, cwd=wt, check_=False)
        if m.returncode != 0:
            say(number, head, "conflict", f"reflex: `{head[:7]}` does not merge cleanly onto main. "
                "Merge main into this branch (keep both sides) and push; the reflex looks again on every push and comment.")
            return "conflict"

        # 2. the constraint, then the tests
        result = check.evaluate("origin/main", ref)
        if not result["ok"]:
            lines = "\n".join(f"- {p}" for p in result["problems"])
            say(number, head, "red", f"reflex: `{head[:7]}` changes the trail in a way the trail does not allow:\n{lines}\n\n"
                "Entries are only ever added. Put the change in a new entry beside the old one.")
            return "red: check"
        ok, out = run_tests_in(wt)
        if not ok:
            say(number, head, "red", f"reflex: tests fail on `{head[:7]}` merged with main:\n```\n{out}\n```")
            return "red: tests"
    finally:
        sh("git", "worktree", "remove", "--force", str(wt), check_=False)

    # 3. entries only -> merge now
    author = author_name(pr)
    if result["entries_added"] == 0 and result["other_changes"] == 0 and result["entries_restored"] == 0:
        say(number, head, "empty", f"reflex: `{head[:7]}` changes nothing relative to main. Nothing to do.")
        return "empty"
    if result["entries_only"]:
        n = result["entries_added"]
        return merge(number, head, title, f"reflex: `{head[:7]}` adds {n} {'entry' if n == 1 else 'entries'} and changes nothing else, so it merges now.")

    # 4. quorum
    d = dial.read()
    reps = reports(number, head)
    counted = {n: r for n, r in reps.items() if n != author}
    fails = [n for n, r in counted.items() if not r["ok"]]
    oks = [n for n, r in counted.items() if r["ok"]]
    if fails:
        say(number, head, "fail-" + "-".join(sorted(fails))[:40], f"reflex: `{head[:7]}` has a `run: fail` from {', '.join(sorted(fails))}. Waiting for a new push.")
        return "waiting: a fail report"
    if len(oks) >= d["quorum"]:
        return merge(number, head, title, f"reflex: `{head[:7]}` passed check and tests, and has {len(oks)} run reports from names other than the author's ({', '.join(sorted(oks))}); quorum is {d['quorum']}. Merging.")
    have = f"has {len(oks)} ({', '.join(sorted(oks))})" if oks else "has none yet"
    say(number, head, "wait", f"reflex: `{head[:7]}` passes check and tests on main, and changes {result['other_changes']} file(s) outside `entries/`, "
        f"so it merges when {d['quorum']} run reports from names other than **{author}** name this head; it {have}.\n\n"
        f"To report, run it and comment one line: `run: ok {head[:7]} by <your name>` (or `run: fail ...`, with what you saw).")
    return f"waiting: {len(oks)}/{d['quorum']}"


def merge(number: int, head: str, title: str, why: str) -> str:
    r = sh("gh", "pr", "merge", str(number), "--merge", "--subject", f"merge #{number}: {title}"[:200],
           "--body", why, check_=False)
    if r.returncode != 0:
        msg = (r.stderr or r.stdout).strip()
        print(f"reflex: merge of #{number} failed: {msg}")
        say(number, head, "merge-failed", f"reflex: tried to merge and could not:\n```\n{msg[-1500:]}\n```\nIf this says permissions, the repository's Actions settings need write access.")
        return "merge failed"
    print(f"reflex: merged #{number}")
    say(number, head, "merge", why)
    consolidate.main([])
    return "merged"


def stale(prs: list[dict], days: int) -> None:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    for pr in prs:
        if pr.get("draft"):
            continue
        updated = dt.datetime.fromisoformat(pr["updated_at"].replace("Z", "+00:00"))
        if updated < cutoff:
            n = pr["number"]
            print(f"reflex: closing #{n}, untouched for {days} days")
            sh("gh", "pr", "close", str(n), "--comment",
               f"reflex: no activity for {days} days (dial `stale_days`), so this is closed to keep the surface small. "
               "Nothing is lost: the branch and every commit stay, and anyone may reopen it.", check_=False)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not REPO:
        print("reflex: GH_REPO is not set", file=sys.stderr)
        return 2
    if len(argv) == 2 and argv[0] == "pr":
        print(f"#{argv[1]}: {look(int(argv[1]))}")
        return 0
    if argv == ["all"]:
        prs = gh_json(f"repos/{REPO}/pulls?state=open&per_page=100", paginate=True)
        for pr in sorted(prs, key=lambda p: p["number"]):
            try:
                print(f"#{pr['number']}: {look(pr['number'])}")
            except subprocess.CalledProcessError as e:
                print(f"#{pr['number']}: error: {e.stderr.strip()[-500:]}")
        stale(prs, dial.read()["stale_days"])
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
