"""The button: an entry from a form instead of a terminal.

Run by .github/workflows/entry.yml when someone presses "Run workflow" on the add-an-entry
workflow and types a name and a text. It writes the entry by tools/entry.py's rules, commits it
as the named author, runs the append-only check on it, pushes it to main and consolidates, which
is what a direct push by whoever pressed the button comes to; only someone who could push to main
can press it. A pull request is not opened, because one opened with a workflow's own token wakes
no workflow and needs a setting most repositories do not have. What happened is written to the
run's summary page from what is on main afterwards, not from what each step meant to do.

    ENTRY_NAME=owner ENTRY_KIND=note ENTRY_TEXT='...' python3 tools/button.py [--dry-run]

A form field is one line, so " // " (with spaces around it) in the text starts a new paragraph.
With --dry-run the entry is written and committed on a local branch, and nothing is pushed.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import io
import os
import pathlib
import re
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check  # noqa: E402
import entry  # noqa: E402

ROOT = entry.ROOT
PARAGRAPH_BREAK = re.compile(r"(?:(?<=\s)|^)//(?=\s|$)")  # spaces on both sides, so a link's :// is left alone
# git's words for "main has commits you do not have": the first three when the push arrives late,
# the last two when main moves while the push is being received. Any other refusal is not retried.
MAIN_MOVED = ("non-fast-forward", "fetch first", "stale info", "cannot lock ref", "failed to update ref")
# what git strips from the ends of an author name (ident.c); a name made only of these is refused by git
CRUD = " ,:;<>\"'\\"


def paragraphs(text: str) -> str:
    """One line from a form into a body: ' // ' starts a new paragraph; empty parts are dropped."""
    parts = [" ".join(p.split()) for p in PARAGRAPH_BREAK.split(text)]
    return "\n\n".join(p for p in parts if p)


def sh(*args: str, cwd: pathlib.Path = ROOT, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, check=check, capture_output=True, encoding="utf-8")


def summary(text: str) -> None:
    """To the run's summary page when there is one, and always to stdout."""
    print(text, flush=True)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text + "\n\n")


def sentence(text: str) -> str:
    return text if text.endswith((".", ")", "`")) else text + "."


def quoted(text: str) -> str:
    return "\n".join("> " + line for line in text.split("\n"))


def typed(name: str, kind: str, text: str) -> str:
    """What was typed into the form, quoted on the page so a refusal does not lose it."""
    return quoted(f"name: {name}\nkind: {kind}\ntext: {text}")


def author_name(name: str) -> str:
    """The typed name as git will take it as an author: no angle brackets or control characters,
    and not made only of the punctuation git strips from the ends; failing that, the filename's slug."""
    clean = re.sub(r"[<>\x00-\x1f\x7f]", "", name).strip(CRUD)
    return clean or entry.slug(name)


def refusal(stderr: str) -> str:
    """What the far end said when it refused a push, without git's hints about what to do next."""
    lines = [line.strip() for line in (stderr or "").splitlines() if line.strip()]
    said = [line[len("remote:"):].strip() for line in lines if line.startswith("remote:")]
    said += [line for line in lines if line.startswith("!")]
    return " ".join(said) or " ".join(line for line in lines if not line.startswith("hint:"))[-300:]


def failed(e: subprocess.CalledProcessError) -> str:
    """A git command that failed, in a sentence."""
    return f"`{' '.join(str(a) for a in e.cmd[:2])}` failed: {(e.stderr or e.stdout or '').strip()[-300:]}"


def write_entry(name: str, kind: str, text: str, when: dt.datetime, cwd: pathlib.Path = ROOT) -> tuple[str, str]:
    """Build the entry, write it and commit it on a new branch off origin/main, as the named author.
    Returns (branch, filename); raises ValueError with a plain reason when there is no entry to make."""
    name = name.strip()
    kind = (kind or "").strip().lower() or "note"
    if not name:
        raise ValueError("a name is needed: who is writing")
    if not re.fullmatch(r"[a-z][a-z /-]{0,30}", kind):
        raise ValueError("the kind must be one short word, such as note, question, reply, start or end")
    fname, content = entry.build(name, kind, paragraphs(text), when)
    heading = entry.HEADING_RE.match(content.split("\n", 1)[0])  # the name and kind as the heading has them
    if sh("git", "status", "--porcelain", cwd=cwd).stdout.strip():
        raise ValueError("the checkout has uncommitted changes; the button needs a clean one")
    branch = f"entry/{fname[:-3]}"
    sh("git", "checkout", "-q", "-B", branch, "origin/main", cwd=cwd)
    if (cwd / "entries" / fname).exists():  # on main as it is now, not as the checkout had it
        raise ValueError(f"{fname} exists already; try again in a second")
    (cwd / "entries" / fname).write_text(content, encoding="utf-8")
    sh("git", "add", f"entries/{fname}", cwd=cwd)
    # "#7" is kept out of the subject: the reflex reads "#N" in a reverted commit's subject as the
    # pull request it came from, and would comment on pull request 7 about a merge that never was
    subject_name = re.sub(r"#+(?=\d)", "", heading.group(2))
    # the author is whoever typed, at an address that is nobody's: a GitHub noreply address would
    # hang the commit on whichever account has that login. The committer is whatever runs this.
    sh("git", "commit", "-q", "-m", f"entry: {subject_name} {heading.group(3)}",
       f"--author={author_name(name)} <{entry.slug(name)}@button.invalid>", cwd=cwd)
    return branch, fname


def push_to_main(cwd: pathlib.Path = ROOT, attempts: int = 5) -> str:
    """Check the one new commit as consolidate would, then push it to main. If main moved in the
    meantime, rebase the commit onto it and try again; a refusal for any other reason is reported
    as it came, once. Returns the new main's commit id."""
    for attempt in range(attempts):
        if sh("git", "rev-parse", "HEAD", cwd=cwd).stdout == sh("git", "rev-parse", "origin/main", cwd=cwd).stdout:
            raise ValueError("this entry is already on main")
        result = check.evaluate("origin/main", "HEAD", cwd)
        if not result["ok"] or not result["entries_only"]:
            raise ValueError("the check refused it: " + "; ".join(result["problems"] or ["not an entries-only change"]))
        pushed = sh("git", "push", "-q", "origin", "HEAD:refs/heads/main", cwd=cwd, check=False)
        if pushed.returncode == 0:
            return sh("git", "rev-parse", "HEAD", cwd=cwd).stdout.strip()
        if not any(word in (pushed.stderr or "") for word in MAIN_MOVED):
            raise ValueError("the push to main was refused, and not because of the entry. If the words below are about "
                             "a connection, press the button again; if about permissions or protection, main is closed "
                             "to the button. The words: " + refusal(pushed.stderr))
        if attempt == attempts - 1:
            raise ValueError(f"main kept moving under the button, {attempts} times over; press it again")
        print("button: main moved; rebasing onto it and trying again", flush=True)
        sh("git", "fetch", "-q", "origin", "main", cwd=cwd)
        rebased = sh("git", "rebase", "-q", "origin/main", cwd=cwd, check=False)
        if rebased.returncode != 0:
            sh("git", "rebase", "--abort", cwd=cwd, check=False)
            said = (rebased.stdout or "") + (rebased.stderr or "")
            if "CONFLICT" in said:
                raise ValueError("someone else added an entry with the same name in the same second; press the button again")
            raise ValueError("main moved and the entry could not be put back on top of it: " + said.strip()[-300:])
        time.sleep(2)
    raise AssertionError("push_to_main left its loop without pushing or raising")


def run_consolidate() -> tuple[int, str]:
    """tools/consolidate.py on the checkout this runs from: its exit code and the last thing it
    said. It works on the real checkout, so it is imported here and not for a dry run; the tests
    put something else in this function's place."""
    import consolidate  # noqa: E402
    page = os.environ.pop("GITHUB_STEP_SUMMARY", None)  # consolidate runs the tests; they must not write the page
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            code = consolidate.main([])
    finally:
        if page is not None:
            os.environ["GITHUB_STEP_SUMMARY"] = page
    print(out.getvalue(), end="", flush=True)  # the log keeps all of it
    lines = [line for line in out.getvalue().splitlines() if line.strip()]
    return code, (lines[-1].strip() if lines else "nothing")


def settle(sha: str, fname: str, content: str, cwd: pathlib.Path, repo: str) -> int:
    """Consolidate main (again if another writer got in first), then look at origin/main and say
    what is there, which is not always what the step before meant to leave."""
    said = ""
    for _ in range(3):
        code, said = run_consolidate()
        if code == 0:
            break
    sh("git", "fetch", "-q", "origin", "main", cwd=cwd)
    on_main = sh("git", "cat-file", "-e", f"origin/main:entries/{fname}", cwd=cwd, check=False).returncode == 0
    if not on_main:
        undo = sh("git", "log", "--format=%H", "--grep=^Revert", f"{sha}..origin/main", cwd=cwd).stdout.split()
        where = f" (`{undo[-1][:7]}`" + (f": https://github.com/{repo}/commit/{undo[-1]}" if repo else "") + ")" if undo else ""
        summary(f"It landed as `{sha[:7]}`, but main did not pass its tests with it, so the reflex took it out "
                f"again{where}. The words are kept in main's history, not on the trail. Pressing again would come "
                "to the same; leave a comment on any pull request saying so, and whoever reads it can look.")
        return 1
    trail = sh("git", "show", "origin/main:TRAIL.md", cwd=cwd, check=False).stdout
    if "\n" + content + "\n" in trail:  # the trail holds each entry's text as it is, this one included
        summary("The trail is regenerated" + (f": https://github.com/{repo}/blob/main/TRAIL.md" if repo else "") + ".")
        return 0
    summary(f"The entry is on main, but the trail page does not show it yet: the consolidation after it stopped "
            f"at `{said}`. The next landing on main tries again. Pressing again would add the entry a second time; "
            "if the trail stays as it is, leave a comment on any pull request, and whoever reads it can look.")
    return 1


def main(argv=None, cwd: pathlib.Path = ROOT) -> int:
    argv = sys.argv[1:] if argv is None else argv
    dry = "--dry-run" in argv
    name = os.environ.get("ENTRY_NAME", "")
    kind = os.environ.get("ENTRY_KIND", "note")
    text = os.environ.get("ENTRY_TEXT", "")
    repo = os.environ.get("GH_REPO", "")
    try:
        branch, fname = write_entry(name, kind, text, dt.datetime.now(dt.timezone.utc), cwd)
    except ValueError as e:
        summary(f"Nothing was added: {sentence(str(e))} Fix that and press the button again; what you typed is below.\n\n"
                + typed(name, kind, text))
        return 2
    except subprocess.CalledProcessError as e:
        summary(f"Nothing was added: {sentence(failed(e))} What you typed is below; press the button again, and if it "
                "comes to the same, leave a comment on any pull request.\n\n" + typed(name, kind, text))
        return 2
    content = (cwd / "entries" / fname).read_text(encoding="utf-8").rstrip("\n")
    summary(f"Written as `entries/{fname}`:\n\n" + quoted(content))
    if dry:
        summary(f"Dry run: committed on branch `{branch}`; nothing pushed.")
        return 0
    try:
        sha = push_to_main(cwd)
    except ValueError as e:
        summary(f"It did not land: {sentence(str(e))}")
        return 1
    except subprocess.CalledProcessError as e:
        summary(f"It did not land: {sentence(failed(e))} Press the button again.")
        return 1
    summary(f"On main as `{sha[:7]}`" + (f": https://github.com/{repo}/commit/{sha}" if repo else "") + ".")
    try:
        return settle(sha, fname, content, cwd, repo)
    except subprocess.CalledProcessError as e:
        summary(f"The entry is on main, but the consolidation after it stopped: {sentence(failed(e))} "
                "The next landing on main regenerates the trail with this entry in it; there is no need to press again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
