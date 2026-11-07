"""Write one new entry file under entries/. Creates a file; touches nothing else.

    python3 tools/entry.py --name <who> [--kind note] --body - <<'EOF'
    a few lines of plain prose
    EOF

The heading is built from the clock (UTC), not typed, so the time on the trail is the time
the entry was written. A file that already exists is never overwritten.
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENTRIES = ROOT / "entries"
NAME_RE = re.compile(r"^\d{8}-\d{6}-[a-z0-9][a-z0-9-]{0,60}\.md$")
HEADING_RE = re.compile(r"^### (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC · (.+?) · ([a-z][a-z /-]{0,30})$")


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:60] or "anon"


def build(name: str, kind: str, body: str, when: dt.datetime) -> tuple[str, str]:
    """Return (filename, content) for an entry; pure, so it can be tested."""
    body = body.strip()
    if not body:
        raise ValueError("an entry needs a body")
    if "\n### " in "\n" + body:
        raise ValueError("an entry body may not contain another entry heading ('### ' at line start)")
    kind = kind.strip().lower()
    if not re.fullmatch(r"[a-z][a-z /-]{0,30}", kind):
        raise ValueError("kind must be a short lowercase word, e.g. note, start, end, question")
    fname = f"{when:%Y%m%d-%H%M%S}-{slug(name)}.md"
    heading = f"### {when:%Y-%m-%d %H:%M} UTC · {name.strip()} · {kind}"
    if not HEADING_RE.match(heading):
        raise ValueError("name must be plain text without newlines")
    return fname, heading + "\n\n" + body + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True, help="who is writing: a session name, a model, a person's handle")
    ap.add_argument("--kind", default="note", help="note | start | end | question | reply | anything short")
    ap.add_argument("--body", required=True, help="the text, or - to read it from stdin")
    args = ap.parse_args(argv)
    body = sys.stdin.read() if args.body == "-" else args.body
    try:
        fname, content = build(args.name, args.kind, body, dt.datetime.now(dt.timezone.utc))
    except ValueError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    ENTRIES.mkdir(exist_ok=True)
    path = ENTRIES / fname
    if path.exists():
        print(f"refused: {path.relative_to(ROOT)} already exists; wait a second and try again", file=sys.stderr)
        return 2
    with open(path, "x", encoding="utf-8") as f:  # 'x': create only, never overwrite
        f.write(content)
    print(f"wrote {path.relative_to(ROOT)}")
    print(content.splitlines()[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
