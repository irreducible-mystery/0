"""field of paths: fifteen sentences in five layers, and every way through them.

    python3 field/field.py                 # walk it: choose one line at each layer
    python3 field/field.py --path 13221    # print one path (five digits, each 1-3)
    python3 field/field.py --all           # print all 243
    python3 field/field.py --make          # regenerate portrait.svg and the views inside field.html
    python3 field/field.py --check         # exit 0 if the lattice is sound, the views are current and self-contained

lattice.json is the record. portrait.svg and the two marked blocks inside field.html are views
of it, generated here; if they disagree with the lattice, the lattice is right.
Python 3, no dependencies, no network.
"""
from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
LATTICE = HERE / "lattice.json"
PORTRAIT = HERE / "portrait.svg"
PAGE = HERE / "field.html"

W, H = 1200, 760
X0, DX = 150, 225          # first column, column spacing
Y0, DY = 190, 180          # first row, row spacing
BAND = 46                  # half-height of the band of threads through one line
INK, PAPER = "#1c1b19", "#f4f0e8"


def load(path: pathlib.Path = LATTICE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def problems(lat: dict) -> list[str]:
    out = []
    layers = lat.get("layers")
    if not isinstance(layers, list) or len(layers) != 5:
        return ["the lattice needs exactly five layers"]
    seen = set()
    for i, layer in enumerate(layers, 1):
        lines = layer.get("lines")
        if not isinstance(layer.get("role"), str) or not layer["role"].strip():
            out.append(f"layer {i}: needs a role")
        if not isinstance(lines, list) or len(lines) != 3:
            out.append(f"layer {i}: needs exactly three lines")
            continue
        for line in lines:
            if not isinstance(line, str) or not line.strip() or "\n" in line:
                out.append(f"layer {i}: every line is one non-empty line of text")
            elif line in seen:
                out.append(f"layer {i}: a line is repeated: {line!r}")
            seen.add(line)
    return out


def all_paths() -> list[str]:
    return ["".join(p) for p in itertools.product("123", repeat=5)]


def sentences(lat: dict, path: str) -> list[str]:
    return [lat["layers"][k]["lines"][int(d) - 1] for k, d in enumerate(path)]


def offset(path: str, k: int) -> float:
    """Where this thread sits inside the band of 81 that pass through its line at layer k.
    Neighbours first, so threads that arrive together and leave together lie together."""
    order = sorted((j for j in range(5) if j != k), key=lambda j: (abs(j - k), j))
    rank = 0
    for j in order:
        rank = rank * 3 + int(path[j]) - 1
    return (rank - 40) / 40 * BAND


def thread(path: str) -> str:
    pts = [(X0 + k * DX, Y0 + (int(d) - 1) * DY + offset(path, k)) for k, d in enumerate(path)]
    d = f"M{pts[0][0] - 60:.0f},{pts[0][1]:.1f} L{pts[0][0]:.0f},{pts[0][1]:.1f}"
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        mid = (x1 + x2) / 2
        d += f" C{mid:.0f},{y1:.1f} {mid:.0f},{y2:.1f} {x2:.0f},{y2:.1f}"
    d += f" L{pts[-1][0] + 60:.0f},{pts[-1][1]:.1f}"
    return d


def weave(lat: dict) -> str:
    """The 243 threads and the five role labels, as an SVG fragment."""
    out = ['<g class="threads" fill="none" stroke="%s" stroke-width="0.8" stroke-opacity="0.2">' % INK]
    for p in all_paths():
        out.append(f'<path data-p="{p}" d="{thread(p)}"/>')
    out.append("</g>")
    out.append('<g class="roles" font-family="Georgia, \'Times New Roman\', serif" font-size="17" '
               'font-style="italic" fill="%s" fill-opacity="0.75" text-anchor="middle">' % INK)
    for k, layer in enumerate(lat["layers"]):
        out.append(f'<text x="{X0 + k * DX}" y="{Y0 + 2 * DY + BAND + 52}">{esc(layer["role"])}</text>')
    out.append("</g>")
    return "\n".join(out)


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def portrait(lat: dict) -> str:
    caption = (f'{esc(lat["title"])} \u00b7 243 ways through 15 sentences, drawn at once \u00b7 '
               f'{esc(lat["by"])} \u00b7 {esc(lat["made"])}')
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
        f'aria-label="243 thin threads crossing five columns of three bands each; every thread is one '
        f'five-sentence path through the lattice.">',
        f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
        weave(lat),
        f'<text x="{W / 2:.0f}" y="{H - 28}" font-family="Georgia, \'Times New Roman\', serif" font-size="14" '
        f'fill="{INK}" fill-opacity="0.6" text-anchor="middle">{caption}</text>',
        "</svg>",
        "",
    ])


def page(lat: dict, current: str) -> str:
    """field.html with its two generated blocks replaced; everything else is left as written."""
    data = json.dumps(lat, ensure_ascii=False, indent=1).replace("</", "<\\/")
    blocks = {
        "LATTICE": f'<script id="lattice" type="application/json">\n{data}\n</script>',
        "WEAVE": f'<svg id="weave" viewBox="0 0 {W} {H - 60}" role="img" aria-label="243 threads, one for '
                 f'each path through the fifteen sentences">\n{weave(lat)}\n</svg>',
    }
    for name, body in blocks.items():
        pat = re.compile(rf"(<!--{name}-->\n).*?(<!--/{name}-->)", re.S)  # the block may be empty
        if len(pat.findall(current)) != 1:
            raise ValueError(f"field.html needs exactly one <!--{name}--> ... <!--/{name}--> block")
        current = pat.sub(lambda m: m.group(1) + body + "\n" + m.group(2), current)
    return current


def outside(html: str) -> list[str]:
    """Anything in the page that would make a browser ask another machine for something.
    The page is meant to work from a download, alone; the only link allowed is to a path (#...)."""
    found = re.findall(r"""(?:src|href|action)\s*=\s*["']?([^"'\s>]+)""", html, re.I)
    found = [u for u in found if not u.startswith("#")]
    found += re.findall(r"""(?<![\w.])(?:https?:)?//[\w.-]+\.[a-z]{2,}[^\s"'<>)]*""", html, re.I)
    found += re.findall(r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon|importScripts)\b|@import|url\(", html)
    return sorted({u for u in found if u != "http://www.w3.org/2000/svg"})


def show(lat: dict, path: str) -> str:
    return "\n".join(sentences(lat, path))


def walk(lat: dict) -> int:
    path = ""
    for k, layer in enumerate(lat["layers"], 1):
        print(f"\n{k} of 5 \u00b7 {layer['role']}")
        for i, line in enumerate(layer["lines"], 1):
            print(f"  {i}  {line}")
        while True:
            try:
                got = input("  1, 2 or 3: ").strip()
            except EOFError:
                print("\nstopped; nothing was chosen past this point.")
                return 1
            if got in {"1", "2", "3"}:
                path += got
                break
    print(f"\npath {path}, one of 243:\n\n{show(lat, path)}\n")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--path", help="five digits, each 1-3")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--make", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    try:
        return run(args)
    except (OSError, ValueError) as e:  # a missing or malformed file: say so, no traceback
        print(f"refused: {e}", file=sys.stderr)
        return 2


def run(args) -> int:
    lat = load()
    bad = problems(lat)
    if bad:
        for b in bad:
            print("  " + b, file=sys.stderr)
        print("NOT OK: the lattice is malformed", file=sys.stderr)
        return 1

    if args.make:
        PORTRAIT.write_text(portrait(lat), encoding="utf-8")
        PAGE.write_text(page(lat, PAGE.read_text(encoding="utf-8")), encoding="utf-8")
        print("wrote field/portrait.svg and the generated blocks of field/field.html")
        return 0
    if args.check:
        stale = []
        if not PORTRAIT.exists() or PORTRAIT.read_text(encoding="utf-8") != portrait(lat):
            stale.append("portrait.svg")
        current = PAGE.read_text(encoding="utf-8")
        if page(lat, current) != current:
            stale.append("field.html")
        texts = {show(lat, p) for p in all_paths()}
        if stale:
            print("NOT OK: stale views (run --make): " + ", ".join(stale))
            return 1
        refs = outside(current) + outside(PORTRAIT.read_text(encoding="utf-8"))
        if refs:
            print("NOT OK: a view refers to something outside itself: " + ", ".join(refs))
            return 1
        print(f"ok: 5 layers, 15 lines, {len(texts)} distinct paths; portrait.svg and field.html are current "
              "and refer to nothing outside themselves")
        return 0
    if args.all:
        for p in all_paths():
            print(f"{p}\n{show(lat, p)}\n")
        return 0
    if args.path:
        if not re.fullmatch(r"[123]{5}", args.path):
            print("refused: a path is five digits, each 1, 2 or 3", file=sys.stderr)
            return 2
        print(show(lat, args.path))
        return 0
    return walk(lat)


if __name__ == "__main__":
    sys.exit(main())
