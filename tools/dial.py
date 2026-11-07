"""Read dial.yml without a YAML library: `key: value` lines, `#` comments, nothing else."""
from __future__ import annotations

import pathlib

DEFAULTS = {"quorum": 2, "stale_days": 30}
ROOT = pathlib.Path(__file__).resolve().parent.parent


def read(path: pathlib.Path | None = None) -> dict:
    path = path or ROOT / "dial.yml"
    out = dict(DEFAULTS)
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = (s.strip() for s in line.split(":", 1))
        if key in out:
            try:
                out[key] = int(value)
            except ValueError:
                pass  # a bad value leaves the default; the dial is a dial, not a gate
    out["quorum"] = max(1, out["quorum"])
    out["stale_days"] = max(1, out["stale_days"])
    return out


if __name__ == "__main__":
    for k, v in read().items():
        print(f"{k}: {v}")
