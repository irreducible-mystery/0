#!/usr/bin/env python3
"""rotation.py - the numbers behind "Lenses, not truths", and a kit for running the pilot.

The notes this file ships with build out a sketch: give the same claim to several models
through several prior frameworks ("lenses"), one fresh instance per cell, and read the grid.
This program does two things.

  1. With no arguments it recomputes every number the notes mark [computed]: the arithmetic
     of shared priors (A), what a rotation can and cannot identify (B), and a toy in which
     lenses are estimators and readers are noisy (C), with a control beside each claim so a
     check cannot pass by being empty.

  2. With a subcommand it is the pilot kit. Nothing in it calls a model: it writes the
     schedule and the prompts, a person pastes them, and it scores the sheet that comes back.

Usage:
    python3 rotation.py                      # run every check (about twelve seconds)
    python3 rotation.py -v                   # also print the tables
    python3 rotation.py plan --models a,b,c  # schedule + empty recording sheet (CSV)
    python3 rotation.py prompt monotone      # the paste-verbatim first message, and its hash
    python3 rotation.py score sheet.csv      # verdicts from a filled sheet

Standard library only. No network. Nothing is written unless you redirect it. Exit status 0
if every check passes, 1 otherwise. Randomness is SHA-256 in counter mode, so the numbers are
the same on every machine.
"""
from __future__ import annotations

import csv
import hashlib
import io
import math
import sys
from itertools import combinations

VERBOSE = False
RESULTS: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str) -> None:
    RESULTS.append((bool(ok), name, detail))
    print(("ok   " if ok else "FAIL ") + name + "  " + detail)


def say(text: str) -> None:
    if VERBOSE:
        print(text)


# --------------------------------------------------------------------------- randomness


class Rng:
    """SHA-256 in counter mode. Same stream everywhere."""

    def __init__(self, seed: str) -> None:
        self.seed = seed.encode()
        self.n = 0
        self.pool: list[float] = []
        self.spare: float | None = None

    def u(self) -> float:
        if not self.pool:
            digest = hashlib.sha256(self.seed + b":" + str(self.n).encode()).digest()
            self.n += 1
            self.pool = [(int.from_bytes(digest[i : i + 8], "big") >> 11) / 2**53 for i in (0, 8, 16, 24)]
        return self.pool.pop()

    def gauss(self) -> float:
        if self.spare is not None:
            z, self.spare = self.spare, None
            return z
        r = math.sqrt(-2.0 * math.log(1.0 - self.u()))
        t = 2.0 * math.pi * self.u()
        self.spare = r * math.sin(t)
        return r * math.cos(t)

    def shuffle(self, items: list) -> list:
        items = list(items)
        for i in range(len(items) - 1, 0, -1):
            j = int(self.u() * (i + 1))
            items[i], items[j] = items[j], items[i]
        return items


# --------------------------------------------------------------------------- rank agreement


def ranks(values: list[float]) -> list[float]:
    """Average ranks; equal values share a rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and abs(values[order[j + 1]] - values[order[i]]) < 1e-9:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2.0
        i = j + 1
    return out


def pearson(a: list[float], b: list[float]) -> float | None:
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va < 1e-12 or vb < 1e-12:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)


def spearman(a: list[float], b: list[float]) -> float | None:
    """Rank correlation, ties allowed. None when either side ranks nothing (all tied)."""
    return pearson(ranks(a), ranks(b))


def rho0(a: list[float], b: list[float]) -> float:
    """Spearman as agreement between two answers. An answer that ranks nothing (all tied, or
    a refusal) agrees fully with another that ranks nothing, and not at all with a ranking."""
    r = spearman(a, b)
    if r is not None:
        return r
    flat = lambda v: max(v) - min(v) < 1e-9
    return 1.0 if flat(a) and flat(b) else 0.0


def mean(xs) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


# --------------------------------------------------------------------------- A. shared priors


def ceiling(a: float, shared: float, own: float, k: float) -> float:
    """Correlation with the truth of the average of k judges, each a*T + shared part + own part."""
    return a / math.sqrt(a * a + shared + own / k)


def section_a() -> None:
    # The two inputs are the SPU figures as the sketch reports them. Not checked by me.
    acc, agr, k = 0.33, 0.52, 13
    a2 = acc * acc
    b2 = agr - a2  # variance each judge shares with the others and not with the truth
    c2 = 1.0 - agr  # variance that is the judge's own
    share = b2 / agr
    say(f"  one-factor model: truth {a2:.3f}, shared-not-truth {b2:.3f}, own {c2:.3f} of each judge's variance")
    check("A1", abs(share - 0.79) < 0.005, f"{share:.0%} of the agreement between two judges is the shared prior, {1 - share:.0%} is the truth")

    err_rho = b2 / (b2 + c2)  # correlation between two judges' errors
    n_eff = k / (1 + (k - 1) * err_rho)
    limit = 1 / err_rho
    check("A2", abs(n_eff - 1.99) < 0.02 and abs(limit - 2.17) < 0.02, f"thirteen judges carry {n_eff:.2f} independent errors' worth; a million would carry {limit:.2f}")

    c13, cinf = ceiling(acc, b2, c2, k), ceiling(acc, b2, c2, 1e12)
    check("A3", abs(c13 - 0.442) < 0.002 and abs(cinf - 0.458) < 0.002, f"averaging all 13 reaches {c13:.3f} with the truth; averaging infinitely many reaches {cinf:.3f}, never more")

    # Monte Carlo: build the judges and measure, rather than trust the algebra.
    rng = Rng("A4")
    n = 20000
    a, b, c = acc, math.sqrt(b2), math.sqrt(c2)
    truth = [rng.gauss() for _ in range(n)]
    prior = [rng.gauss() for _ in range(n)]
    judges = [[a * t + b * s + c * rng.gauss() for t, s in zip(truth, prior)] for _ in range(k)]
    m_acc = mean(pearson(j, truth) for j in judges)
    m_agr = mean(pearson(x, y) for x, y in combinations(judges, 2))
    avg = [sum(col) / k for col in zip(*judges)]
    m_avg = pearson(avg, truth)
    check("A4", abs(m_acc - acc) < 0.02 and abs(m_agr - agr) < 0.02 and abs(m_avg - c13) < 0.02, f"simulated: accuracy {m_acc:.3f}, agreement {m_agr:.3f}, average of 13 {m_avg:.3f}")

    # Control: with no shared prior the same 13 judges would average their way much closer.
    free = ceiling(acc, 0.0, 1 - a2, k)
    check("A5", free > 0.75, f"control: the same judges with independent errors would reach {free:.3f}; the gap to {c13:.3f} is the common mode")


# --------------------------------------------------------------------------- B. what a rotation identifies


def section_b() -> None:
    acc, agr = 0.33, 0.52
    a2 = acc * acc
    b2 = agr - a2
    # Each lens f swaps the shared prior S for its own S_f; two lenses' priors correlate r.
    rows = []
    for r in (1.0, 0.5, 0.0):
        within = a2 + b2  # same lens, different model
        across = a2 + b2 * r  # different lens
        four = acc / math.sqrt(a2 + b2 * (1 + 3 * r) / 4)  # average over 4 lenses, many models each
        rows.append((r, within, across, four))
        say(f"  r={r:.1f}: within-lens agreement {within:.2f}, across-lens {across:.2f}, four-lens average vs truth {four:.3f}")
    check("B1", abs(rows[0][3] - 0.458) < 0.002 and abs(rows[1][3] - 0.546) < 0.002 and abs(rows[2][3] - 0.717) < 0.002,
          f"four lenses lift the ceiling from {rows[0][3]:.3f} (lenses identical) to {rows[1][3]:.3f} (half shared) to {rows[2][3]:.3f} (nothing shared)")
    check("B2", abs((rows[1][1] - rows[1][2]) - b2 * 0.5) < 1e-12, f"within-lens minus across-lens agreement is b2*(1-r): {rows[1][1] - rows[1][2]:.3f} at r=0.5; that gap is what the grid measures")

    # Level 2 as an identity: two different worlds, the same grid.
    world_1 = (0.30, 0.10)  # (truth a2, what every lens shares b2*r): mostly truth
    world_2 = (0.10, 0.30)  # mostly a prior all lenses share
    check("B3", abs(sum(world_1) - sum(world_2)) < 1e-12 and world_1 != world_2,
          f"across-lens agreement is a2 + b2*r: truth {world_1[0]} + shared {world_1[1]} and truth {world_2[0]} + shared {world_2[1]} give the same grid, {sum(world_1):.2f}; no rotation tells them apart")


# --------------------------------------------------------------------------- C. the toy: lenses as estimators


def pav(y: list[float]) -> list[float]:
    """Isotonic (non-decreasing) least squares, pool adjacent violators."""
    blocks: list[list[float]] = []  # [sum, count]
    for v in y:
        blocks.append([v, 1])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1] + 1e-12:
            s, c = blocks.pop()
            blocks[-1][0] += s
            blocks[-1][1] += c
    out: list[float] = []
    for s, c in blocks:
        out.extend([s / c] * int(c))
    return out


def iso(y: list[float], up: bool) -> list[float]:
    return pav(y) if up else [-v for v in pav([-v for v in y])]


def sse(a: list[float], b: list[float]) -> float:
    return sum((x - z) ** 2 for x, z in zip(a, b))


def lens_bare(y: list[float], sigma: float) -> list[float]:
    """No lens: the evidence as it came."""
    return list(y)


def lens_monotone(y: list[float], sigma: float) -> list[float]:
    """Only up or only down; anything else is noise to be smoothed away."""
    up, down = iso(y, True), iso(y, False)
    return up if sse(up, y) <= sse(down, y) else down


def lens_more_is_more(y: list[float], sigma: float) -> list[float]:
    """The monotone lens with its direction taken from the claim instead of the evidence:
    more never hurts. Not one of the four; used once, in C1."""
    return iso(y, True)


def lens_nonmonotone(y: list[float], sigma: float) -> list[float]:
    """Up, then down, with the turning point wherever it fits best (the ends included)."""
    best = None
    for k in range(-1, len(y)):
        fit = iso(y[: k + 1], True) + iso(y[k + 1 :], False)
        e = sse(fit, y)
        if best is None or e < best[0] - 1e-12:
            best = (e, fit)
    return best[1]


CHI2_5DF_95 = 11.07


def lens_skeptical(y: list[float], sigma: float) -> list[float]:
    """Assume there is no effect. Rank only if the evidence refuses to be flat."""
    m = sum(y) / len(y)
    if sum((v - m) ** 2 for v in y) / (sigma * sigma) < CHI2_5DF_95:
        return [m] * len(y)
    return list(y)


def solve(mat: list[list[float]], rhs: list[float]) -> list[float] | None:
    n = len(rhs)
    m = [row[:] + [r] for row, r in zip(mat, rhs)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(m[r][i]))
        if abs(m[p][i]) < 1e-12:
            return None
        m[i], m[p] = m[p], m[i]
        for r in range(n):
            if r != i:
                f = m[r][i] / m[i][i]
                m[r] = [x - f * z for x, z in zip(m[r], m[i])]
    return [m[i][n] / m[i][i] for i in range(n)]


MECH_TAUS = (0.5, 1.0, 2.0, 4.0)


def lens_mechanistic(y: list[float], sigma: float) -> list[float]:
    """Only curves a named mechanism can make: a benefit that saturates, minus a cost that
    grows with the dose. c + A*(1 - exp(-x/tau)) - B*x with A, B >= 0."""
    n = len(y)
    best = None
    for tau in MECH_TAUS:
        g = [1 - math.exp(-x / tau) for x in range(n)]
        h = [-float(x) for x in range(n)]
        one = [1.0] * n
        for cols in ([one, g, h], [one, g], [one, h], [one]):
            mat = [[sum(p * q for p, q in zip(u, v)) for v in cols] for u in cols]
            rhs = [sum(p * q for p, q in zip(u, y)) for u in cols]
            coef = solve(mat, rhs)
            if coef is None or any(c < 0 for c in coef[1:]):
                continue
            fit = [sum(c * col[i] for c, col in zip(coef, cols)) for i in range(n)]
            e = sse(fit, y)
            if best is None or e < best[0] - 1e-12:
                best = (e, fit)
    return best[1]


LENSES = {
    "bare": lens_bare,
    "monotone": lens_monotone,
    "non-monotone": lens_nonmonotone,
    "skeptical": lens_skeptical,
    "mechanistic": lens_mechanistic,
    "more-is-more": lens_more_is_more,
}
FOUR = ["monotone", "non-monotone", "skeptical", "mechanistic"]

WORLDS = {
    "rising": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
    "saturating": [round(1 - math.exp(-x / 1.2), 4) for x in range(6)],
    "peak": [0.0, 0.6, 1.0, 0.8, 0.4, 0.1],
    "threshold": [0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
    "flat": [0.0] * 6,
}
SIGMA = 0.15  # noise on each dose's measured mean, per reading
READER_SD = 0.12  # each reader's own persistent slant, drawn once per trial
READERS = 3
REPS = 2
TRIALS = 400


def draw_grid(rng: Rng, truth: list[float], names: list[str], drift: float = 0.0) -> dict:
    """One trial: ans[(reader, lens, rep)] is the curve that cell would rank the candidates by.
    Every cell is a fresh run, so every cell reads its own noisy evidence. A reader's slant
    persists across all its cells. `drift` is an error in the instrument itself, the same for
    everyone."""
    ans = {}
    for m in range(READERS):
        slant = [READER_SD * rng.gauss() for _ in truth]
        for f in names:
            for r in range(REPS):
                ev = [t + s + drift * x + SIGMA * rng.gauss() for x, (t, s) in enumerate(zip(truth, slant))]
                ans[(m, f, r)] = LENSES[f](ev, SIGMA)
    return ans


def grid_stats(ans: dict) -> dict:
    """What a full grid with replicates can measure with no ground truth. Keys of `ans` are
    (model, lens, rep); values are score lists. Agreement is mean Spearman over pairs of runs.
      floor       same model, same lens, run again
      within      same lens, different model
      across      same model, different lens
      own[f]      the floor for lens f alone: how stable is the answer under this lens
      out[f]      lens f against every other lens, same model
    """
    floor, within, across = [], [], []
    lenses = sorted({k[1] for k in ans})
    own = {f: [] for f in lenses}
    out = {f: [] for f in lenses}
    for (k1, x), (k2, y) in combinations(sorted(ans.items()), 2):
        rho = rho0(x, y)
        same_model, same_lens = k1[0] == k2[0], k1[1] == k2[1]
        if same_model and same_lens:
            floor.append(rho)
            own[k1[1]].append(rho)
        elif same_lens:
            within.append(rho)
        elif same_model:
            across.append(rho)
            out[k1[1]].append(rho)
            out[k2[1]].append(rho)
    m = lambda xs: mean(xs) if xs else None
    return {"floor": m(floor), "within": m(within), "across": m(across),
            "own": {f: m(v) for f, v in own.items()}, "out": {f: m(v) for f, v in out.items()}}


def n_effective(curves: list[list[float]]) -> float:
    """How many lenses the set behaves as: (trace C)^2 / trace(C^2) for the agreement matrix C."""
    f = len(curves)
    total = sum(rho0(a, b) ** 2 for a in curves for b in curves)
    return f * f / total if total > 0 else float("nan")


def top(curve: list[float]) -> int | None:
    """Index of the single best candidate, or None if the answer does not name one."""
    hi = max(curve)
    best = [i for i, v in enumerate(curve) if abs(v - hi) < 1e-9]
    return best[0] if len(best) == 1 else None


def section_c() -> None:
    names = ["bare"] + FOUR
    acc = {w: {f: [] for f in names} for w in WORLDS}
    agree_same_lens = {w: {f: [] for f in names} for w in WORLDS}
    stats = {w: [] for w in WORLDS}
    neff = {w: [] for w in WORLDS}
    abstain = {f: 0 for f in names}
    for w, truth in WORLDS.items():
        rng = Rng("C:" + w)
        for _ in range(TRIALS):
            ans = draw_grid(rng, truth, names)
            for f in names:
                for m in range(READERS):
                    acc[w][f].append(rho0(ans[(m, f, 0)], truth))
                    if w == "flat" and spearman(ans[(m, f, 0)], list(range(6))) is None and len(set(ans[(m, f, 0)])) == 1:
                        abstain[f] += 1
                for m1, m2 in combinations(range(READERS), 2):
                    agree_same_lens[w][f].append(rho0(ans[(m1, f, 0)], ans[(m2, f, 0)]))
            stats[w].append(grid_stats({k: v for k, v in ans.items() if k[1] in FOUR}))
            one = [t + SIGMA * rng.gauss() for t in truth]  # one reading, seen through all four
            neff[w].append(n_effective([LENSES[f](one, SIGMA) for f in FOUR]))

    real = [w for w in WORLDS if w != "flat"]
    say("  accuracy (mean Spearman with the truth), by world and lens:")
    say("    " + "world".ljust(12) + "".join(f.rjust(14) for f in names))
    table = {w: {f: mean(acc[w][f]) for f in names} for w in real}
    for w in real:
        say("    " + w.ljust(12) + "".join(f"{table[w][f]:14.3f}" for f in names))

    # C1. The SPU pattern, made on purpose: one lens on everyone, a world it does not fit.
    rng = Rng("C1")
    agree1, acc1 = [], []
    for _ in range(TRIALS):
        ans = draw_grid(rng, WORLDS["peak"], ["more-is-more"])
        cells = [ans[(m, "more-is-more", 0)] for m in range(READERS)]
        acc1.extend(rho0(c, WORLDS["peak"]) for c in cells)
        agree1.extend(rho0(x, y) for x, y in combinations(cells, 2))
    check("C1", mean(agree1) > mean(acc1) + 0.1, f"peak world, everyone told more never hurts: readers agree with each other {mean(agree1):.2f} and with the truth {mean(acc1):.2f}")
    a_two = table["peak"]["monotone"]
    g_two = mean(agree_same_lens["peak"]["monotone"])
    check("C1b", g_two < a_two - 0.1 and g_two < 0.4,
          f"same world, the sketch's monotone lens (either direction): with each other {g_two:.2f}, with the truth {a_two:.2f}. No false consensus; the lens flips between 'rising' and 'falling' from run to run")
    a_ctl = table["peak"]["non-monotone"]
    g_ctl = mean(agree_same_lens["peak"]["non-monotone"])
    check("C1c", a_ctl > g_ctl, f"control, same world, everyone non-monotone: with each other {g_ctl:.2f}, with the truth {a_ctl:.2f}; agreement does not outrun accuracy")

    # C2. No lens wins everywhere.
    winners = {w: max(FOUR, key=lambda f: table[w][f]) for w in real}
    worst = {f: min(table[w][f] - max(table[w][g] for g in FOUR) for w in real) for f in FOUR}
    check("C2", len(set(winners.values())) >= 2 and all(v < -0.02 for v in worst.values()),
          "best of the four: " + ", ".join(f"{w} -> {winners[w]}" for w in real) + "; every lens trails the best by at least 0.02 somewhere")
    check("C2b", table["rising"]["monotone"] > table["rising"]["bare"] + 0.03 and table["peak"]["monotone"] < table["peak"]["bare"] - 0.15,
          f"the monotone lens against no lens: rising {table['rising']['monotone']:.2f} vs {table['rising']['bare']:.2f}, peak {table['peak']['monotone']:.2f} vs {table['peak']['bare']:.2f}; a right prior helps, a wrong one costs more")

    # C3. The grid's own reading, no ground truth used.
    avg = {}
    for w in real:
        g = {k: mean(t[k] for t in stats[w]) for k in ("floor", "within", "across")}
        g["own"] = {f: mean(t["own"][f] for t in stats[w]) for f in FOUR}
        g["out"] = {f: mean(t["out"][f] for t in stats[w]) for f in FOUR}
        avg[w] = g
        say(f"    {w.ljust(11)} floor {g['floor']:.2f}  other model {g['within']:.2f}  other lens {g['across']:.2f}"
            + "   own: " + " ".join(f"{g['own'][f]:.2f}" for f in FOUR) + "   out: " + " ".join(f"{g['out'][f]:.2f}" for f in FOUR))
    mean_eff = {w: avg[w]["floor"] - avg[w]["across"] for w in real}
    odd_eff = {w: avg[w]["floor"] - min(avg[w]["out"].values()) for w in real}
    odd = {w: min(FOUR, key=lambda f: avg[w]["out"][f]) for w in real}
    check("C3", odd_eff["peak"] > odd_eff["rising"] + 0.1 and odd["peak"] == "monotone",
          f"lens effect, no truth used (re-run agreement minus the most divergent lens's agreement with the rest): rising {odd_eff['rising']:+.2f}, peak {odd_eff['peak']:+.2f}, and the divergent lens on the peak is {odd['peak']}")
    check("C3b", mean_eff["peak"] < odd_eff["peak"] / 2,
          f"averaged over all lens pairs the same effect reads {mean_eff['peak']:+.2f}: one lens in four splitting is diluted by the three that agree, so report per lens")
    own = {w: avg[w]["own"]["monotone"] for w in real}
    check("C3c", own["peak"] < own["rising"] - 0.3 and avg["peak"]["own"]["non-monotone"] > own["peak"] + 0.3,
          f"a lens's agreement with its own re-run: monotone {own['rising']:.2f} on rising, {own['peak']:.2f} on the peak (non-monotone there: {avg['peak']['own']['non-monotone']:.2f}). A prior that does not fit shows as instability, with no answer key")

    # C4. The sketch's rule, on a grid with nothing to find.
    rng = Rng("C4")
    fired_rank = fired_top = 0
    for _ in range(TRIALS):
        slant = [READER_SD * rng.gauss() for _ in range(6)]
        four = [[t + s + SIGMA * rng.gauss() for t, s in zip(WORLDS["peak"], slant)] for _ in range(4)]  # four runs, one lens
        fired_rank += any(ranks(x) != ranks(four[0]) for x in four[1:])
        fired_top += len({top(x) for x in four}) > 1
    check("C4", fired_top / TRIALS > 0.2,
          f"placebo: one model, the bare lens four times under four labels. 'The answer changes with the framework' fires in {fired_rank / TRIALS:.0%} of trials on the full ranking and {fired_top / TRIALS:.0%} on the top choice alone")

    # C5. How many lenses is four?
    ne = {w: mean(v for v in neff[w] if v == v) for w in real}
    check("C5", all(1.0 <= v < 3.0 for v in ne.values()),
          "the four lenses behave as " + ", ".join(f"{ne[w]:.1f} ({w})" for w in real) + " lenses; never four")

    # C6. A flat world: who declines to rank?
    total = TRIALS * READERS
    check("C6", abstain["skeptical"] / total > 0.5 and all(abstain[f] / total < 0.05 for f in names if f != "skeptical"),
          f"no effect at all: the skeptical lens declines to rank {abstain['skeptical'] / total:.0%} of the time; the others " + ", ".join(f"{abstain[f] / total:.0%}" for f in names if f != "skeptical"))

    # C7. Level 2: an error every lens shares. Truth is the peak; the instrument drifts upward.
    rng = Rng("C7")
    truth = WORLDS["peak"]
    all_acc, all_agree, fixed_acc = [], [], []
    for _ in range(TRIALS):
        ans = draw_grid(rng, truth, FOUR, drift=0.35)
        cells = [ans[(m, f, 0)] for m in range(READERS) for f in FOUR]
        all_acc.extend(rho0(c, truth) for c in cells)
        all_agree.extend(rho0(x, y) for x, y in combinations(cells, 2))
        # Not a lens: a second measurement. A blank run through the same instrument, subtracted.
        for _ in range(READERS):
            reading = [t + 0.35 * x + SIGMA * rng.gauss() for x, t in enumerate(truth)]
            blank = [0.35 * x + SIGMA * rng.gauss() for x in range(6)]
            fixed_acc.append(rho0([e - b for e, b in zip(reading, blank)], truth))
    check("C7", mean(all_agree) > mean(all_acc) + 0.3,
          f"shared instrument drift: all 12 cells agree {mean(all_agree):.2f} with each other and {mean(all_acc):.2f} with the truth. The rules say robust; it is robustly wrong")
    check("C7b", mean(fixed_acc) > mean(all_acc) + 0.3,
          f"what fixes it is not a fifth lens but a blank run through the same instrument: {mean(fixed_acc):.2f} with the truth, noise doubled and all")

    # C8. Which lens is a reader already wearing? Compare its unprompted answer to each lens.
    rng = Rng("C8")
    hits = {f: 0 for f in ("monotone", "non-monotone", "mechanistic")}
    n_id = 200
    for hidden in hits:
        for _ in range(n_id):
            score = {f: [] for f in FOUR}
            for w in real:
                slant = [READER_SD * rng.gauss() for _ in range(6)]
                read = lambda: [t + s + SIGMA * rng.gauss() for t, s in zip(WORLDS[w], slant)]
                unprompted = LENSES[hidden](read(), SIGMA)  # what the reader says with no lens given
                for f in FOUR:
                    score[f].append(rho0(unprompted, LENSES[f](read(), SIGMA)))  # a separate run
            hits[hidden] += max(FOUR, key=lambda f: mean(score[f])) == hidden
    check("C8", all(h / n_id > 0.4 for h in hits.values()),
          "a reader's hidden lens, recovered from four claims by 'which lens run is nearest its unprompted run': " + ", ".join(f"{f} {h / n_id:.0%}" for f, h in hits.items()) + " (chance 25%)")


# --------------------------------------------------------------------------- the pilot kit

# The four frameworks are the sketch's, word for word. `bare` and `ill-posed` are additions.
LENS_TEXT = {
    "bare": "",
    "monotone": (
        "Assume the relationship is monotone: more of the input means more (or consistently less) of the output, "
        "with no reversals, no peaks, no thresholds, no saturation. If the data looks noisy, treat the noise as "
        "measurement error around a monotone trend. Rank the candidates accordingly."
    ),
    "non-monotone": (
        "Assume the relationship may reverse, peak, or saturate. Look for the turning point, the threshold, the "
        "range where more stops helping or starts hurting. Do not smooth a reversal away as noise. Rank the "
        "candidates accordingly, and name the turning point if you find one."
    ),
    "skeptical": (
        "Assume the claimed relationship is false. Your job is to find the counterexample, the case where it "
        "breaks, the confound that explains the pattern. A claim survives only if you cannot break it. Rank the "
        "candidates accordingly, and say what would change your ranking."
    ),
    "mechanistic": (
        "Do not accept a relationship without a mechanism. Name the mechanism that would produce it, and the "
        "observation that would show the mechanism is absent. No mechanism, no claim - correlation alone is not "
        "an answer. Rank the candidates accordingly, and say which mechanism each ranking depends on."
    ),
    "ill-posed": (
        "Before anything else, ask whether the question can be answered as posed: whether its terms mean one "
        "thing, whether the measurement measures what the claim is about, whether one ranking exists at all. "
        "If it cannot be answered as posed, say so, write REFUSE as your ranking, and say what would have to be "
        "pinned down first. Rank the candidates only if the question survives."
    ),
}
CANDIDATES = ["0", "50", "100", "200", "400", "800"]
CLAIM = "As caffeine dose increases, cognitive performance increases."
TASK = (
    "Claim: \"" + CLAIM + "\"\n\n"
    "Candidates: a single oral dose of 0, 50, 100, 200, 400 or 800 mg of caffeine, given to a rested, healthy "
    "adult who normally drinks about one cup of coffee a day. The outcome is their score on a 30-minute "
    "sustained-attention task that starts one hour after the dose.\n\n"
    "Rank the six candidates from best expected score to worst.\n\n"
    "Reply with exactly three lines:\n"
    "RANKING: the six doses, best first, separated by > (use = between doses you cannot separate)\n"
    "CONFIDENCE: a number from 0 to 100\n"
    "REASONING: two or three sentences"
)
SHEET_COLUMNS = ["run", "model", "lens", "rep", "prompt_sha256", "ranking", "confidence", "reasoning"]


def prompt_for(lens: str) -> str:
    text = LENS_TEXT[lens]
    return (text + "\n\n" if text else "") + TASK


def prompt_hash(lens: str) -> str:
    return hashlib.sha256(prompt_for(lens).encode()).hexdigest()[:12]


def make_plan(models: list[str], lenses: list[str], reps: int, seed: str) -> list[dict]:
    """Every model runs every lens `reps` times. Order is shuffled per model, from the seed."""
    rows = []
    for model in models:
        cells = Rng(f"plan:{seed}:{model}").shuffle([(f, r) for f in lenses for r in range(1, reps + 1)])
        for lens, rep in cells:
            rows.append({"run": len(rows) + 1, "model": model, "lens": lens, "rep": rep, "prompt_sha256": prompt_hash(lens), "ranking": "", "confidence": "", "reasoning": ""})
    return rows


def parse_ranking(text: str, candidates: list[str] = CANDIDATES) -> list[float] | None:
    """'200>100=400>50>0>800' -> a score per candidate, in candidate order (higher is better).
    None for REFUSE, blank, or anything that is not each candidate exactly once."""
    text = text.strip().replace("mg", "").replace(" ", "")
    if not text or text.upper().startswith("REFUSE"):
        return None
    score, seen = {}, []
    groups = text.split(">")
    for level, group in enumerate(groups):
        for item in group.split("="):
            score[item] = float(len(groups) - level)
            seen.append(item)
    if sorted(seen) != sorted(candidates):
        raise ValueError(f"not a ranking of {', '.join(candidates)}: {text!r}")
    return [score[c] for c in candidates]


def shape(score: list[float] | None) -> str:
    """What a ranking says about the dose-response curve, read in dose order."""
    if score is None:
        return "refused"
    steps = [(b > a) - (b < a) for a, b in zip(score, score[1:])]
    if all(s == 0 for s in steps):
        return "flat"
    if all(s >= 0 for s in steps):
        return "rising"
    if all(s <= 0 for s in steps):
        return "falling"
    turn = max(i for i, s in enumerate(steps) if s > 0)
    if all(s >= 0 for s in steps[: turn + 1]) and all(s <= 0 for s in steps[turn + 1 :]):
        return "peak"
    return "other"


# Thresholds for the words in the verdict. Stipulated, small, and printed beside the numbers.
EFFECT = 0.10


def score_sheet(rows: list[dict]) -> dict:
    cells = {}
    for row in rows:
        if not row.get("ranking", "").strip():
            continue
        cells[(row["model"], row["lens"], str(row["rep"]))] = parse_ranking(row["ranking"])
    ranked = {k: v for k, v in cells.items() if v is not None}
    # A refusal is an answer: it agrees with another refusal and with no ranking.
    g = grid_stats({k: ([0.0] * len(CANDIDATES) if v is None else v) for k, v in cells.items()})
    out = {"runs": len(cells), "refused": sum(v is None for v in cells.values()), "shapes": {k: shape(v) for k, v in cells.items()}, **g}
    f, w = g["floor"], g["within"]
    outs = {lens: v for lens, v in g["out"].items() if v is not None}
    out["odd"] = min(outs, key=outs.get) if outs else None
    out["lens_effect"] = None if f is None or not outs else f - outs[out["odd"]]
    out["model_effect"] = None if f is None or w is None else f - w
    if f is None:
        out["verdict"] = "no replicates: a change of answer cannot be told from a re-run. Not classified."
    elif out["lens_effect"] is None or out["model_effect"] is None:
        out["verdict"] = "grid incomplete: needs at least two models and two lenses. Not classified."
    else:
        parts = []
        if out["lens_effect"] > EFFECT:
            parts.append(f"framework-dependent (the lens that splits from the rest: {out['odd']})")
        if out["model_effect"] > EFFECT:
            parts.append("model-dependent")
        out["verdict"] = " and ".join(parts) if parts else "robust to these lenses and these models (which is not the same as right)"
    # Which lens is each model already wearing: nearest lens run to its bare run.
    nearest = {}
    for model in sorted({k[0] for k in ranked}):
        bare = [v for k, v in ranked.items() if k[0] == model and k[1] == "bare"]
        if not bare:
            continue
        best = {}
        for lens in sorted({k[1] for k in ranked if k[0] == model and k[1] != "bare"}):
            rhos = [spearman(x, y) for x in bare for k, y in ranked.items() if k[0] == model and k[1] == lens]
            rhos = [r for r in rhos if r is not None]
            if rhos:
                best[lens] = mean(rhos)
        if best:
            nearest[model] = best
    out["nearest"] = nearest
    # Obeyed against itself: the lens run has the lens's shape and the model's own bare run does not.
    obeyed = []
    for (model, lens, rep), s in out["shapes"].items():
        bare_shapes = {v for k, v in out["shapes"].items() if k[0] == model and k[1] == "bare"}
        if lens == "monotone" and s in ("rising", "falling") and bare_shapes and s not in bare_shapes:
            obeyed.append((model, lens, rep, s, sorted(bare_shapes)))
    out["obeyed"] = obeyed
    return out


def print_score(result: dict, truth_shape: str | None) -> None:
    fmt = lambda v: "  n/a" if v is None else f"{v:5.2f}"
    print(f"{result['runs']} runs scored, {result['refused']} refused to rank")
    print("agreement (mean Spearman between rankings)")
    print(f"  same model, same lens, run again   {fmt(result['floor'])}   <- the noise floor")
    print(f"  same lens, different model         {fmt(result['within'])}")
    print(f"  same model, different lens         {fmt(result['across'])}")
    print("per lens:           with its own re-run   with the other lenses")
    for lens in sorted(result["own"]):
        print(f"  {lens:18} {fmt(result['own'][lens])}                 {fmt(result['out'][lens])}")
    print(f"lens effect  (floor - the most divergent lens's agreement with the rest)  {fmt(result['lens_effect'])}   counted above {EFFECT}")
    print(f"model effect (floor - same lens, different model)                         {fmt(result['model_effect'])}   counted above {EFFECT}")
    print("verdict: " + result["verdict"])
    print("shape of each ranking, in dose order" + (f" (ground truth: {truth_shape})" if truth_shape else "") + ":")
    for (model, lens, rep), s in sorted(result["shapes"].items()):
        mark = "" if not truth_shape else ("   matches" if s == truth_shape else "   does not match")
        print(f"  {model:16} {lens:14} rep {rep}  {s}{mark}")
    for model, best in result["nearest"].items():
        order = sorted(best.items(), key=lambda kv: -kv[1])
        print(f"{model} without a lens is nearest to: " + ", ".join(f"{lens} {rho:.2f}" for lens, rho in order))
    for model, lens, rep, s, bare in result["obeyed"]:
        print(f"prior artifact: {model} under '{lens}' (rep {rep}) answered {s}; unprompted it answered {', '.join(bare)}. It followed the lens against its own answer.")


def section_d() -> None:
    """The kit, tested on a sheet whose answer is known because the toy wrote it."""
    models = ["m1", "m2", "m3"]
    lenses = ["bare"] + FOUR
    plan = make_plan(models, lenses, 2, "test")
    cells = {(r["model"], r["lens"], r["rep"]) for r in plan}
    orders = {m: [r["lens"] for r in plan if r["model"] == m] for m in models}
    check("D1", len(plan) == 30 and len(cells) == 30 and len({tuple(o) for o in orders.values()}) == 3 and plan == make_plan(models, lenses, 2, "test"),
          "plan: 3 models x 5 lenses x 2 replicates = 30 runs, every cell once, a different order per model, the same plan from the same seed")
    check("D2", len({prompt_hash(f) for f in LENS_TEXT}) == len(LENS_TEXT) and prompt_for("bare") == TASK and prompt_for("monotone").startswith("Assume the relationship is monotone"),
          "prompts: each lens has its own hash; the bare prompt is the task alone; a lens prompt is the lens, then the task")
    cases = {"800>400>200>100>50>0": "rising", "0>50>100>200>400>800": "falling", "200>100>400>50>0>800": "peak",
             "200=400>100>50>0>800": "peak", "0=50=100=200=400=800": "flat", "0>800>50>400>100>200": "other", "REFUSE": "refused"}
    got = {text: shape(parse_ranking(text)) for text in cases}
    bad = False
    try:
        parse_ranking("200>100>400")
    except ValueError:
        bad = True
    sheet = [{"model": m, "lens": f, "rep": r, "ranking": "REFUSE" if f == "ill-posed" else "200>100>400>50>0>800"}
             for m in ("m1", "m2") for f in ("ill-posed", "non-monotone", "mechanistic") for r in (1, 2)]
    ref = score_sheet(sheet)
    refusal = ref["refused"] == 4 and ref["own"]["ill-posed"] == 1.0 and ref["out"]["ill-posed"] == 0.0 and ref["odd"] == "ill-posed"
    check("D3", got == cases and bad and refusal, "shapes: rising, falling, peak (ties allowed), flat, other and refused are each read correctly; a ranking with a dose missing is rejected; a refusal agrees with a refusal and with no ranking")

    def fill(world: str, seed: str, placebo: bool = False) -> list[dict]:
        rng = Rng(seed)
        slant = {m: [READER_SD * rng.gauss() for _ in range(6)] for m in models}
        rows = make_plan(models, lenses, 2, seed)
        for row in rows:
            ev = [t + s + SIGMA * rng.gauss() for t, s in zip(WORLDS[world], slant[row["model"]])]
            curve = LENSES["bare" if placebo else row["lens"]](ev, SIGMA)
            order = sorted(range(6), key=lambda i: -curve[i])
            text = CANDIDATES[order[0]]
            for i, j in zip(order, order[1:]):
                text += ("=" if abs(curve[i] - curve[j]) < 1e-9 else ">") + CANDIDATES[j]
            row["ranking"] = text
        return rows

    def round_trip(rows: list[dict]) -> dict:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
        return score_sheet(list(csv.DictReader(io.StringIO(buf.getvalue()))))

    peak = [round_trip(fill("peak", f"D4:{i}")) for i in range(40)]
    plac = [round_trip(fill("peak", f"D4:{i}", placebo=True)) for i in range(40)]
    e_peak, e_plac = mean(r["lens_effect"] for r in peak), mean(r["lens_effect"] for r in plac)
    said = sum("framework-dependent" in r["verdict"] for r in plac) / len(plac)
    named = sum(r["odd"] == "monotone" for r in peak) / len(peak)
    found = sum("framework-dependent" in r["verdict"] for r in peak) / len(peak)
    check("D4", e_peak > e_plac + 0.1 and named > 0.8,
          f"score, through CSV and back, 40 sheets each: lens effect {e_peak:+.2f} on a peak world with real lenses (called framework-dependent {found:.0%}, monotone named as the split {named:.0%}), {e_plac:+.2f} when all five lenses are secretly the same (still called framework-dependent {said:.0%} of the time: picking the most divergent of five finds something in noise)")
    one = [r for r in fill("peak", "D5") if r["rep"] == 1]
    check("D5", "Not classified" in round_trip(one)["verdict"], "score: a sheet with one run per cell is not classified, because nothing in it measures the noise")


# --------------------------------------------------------------------------- command line


def cmd_plan(argv: list[str]) -> int:
    opts = {"--models": "model-a,model-b,model-c", "--lenses": "bare,monotone,non-monotone,skeptical,mechanistic", "--reps": "2", "--seed": "pilot"}
    for i in range(0, len(argv) - 1, 2):
        if argv[i] not in opts:
            print(f"unknown option {argv[i]}", file=sys.stderr)
            return 2
        opts[argv[i]] = argv[i + 1]
    lenses = [x for x in opts["--lenses"].split(",") if x]
    unknown = [x for x in lenses if x not in LENS_TEXT]
    if unknown:
        print(f"unknown lens {unknown[0]}; known: {', '.join(LENS_TEXT)}", file=sys.stderr)
        return 2
    writer = csv.DictWriter(sys.stdout, fieldnames=SHEET_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(make_plan([m for m in opts["--models"].split(",") if m], lenses, int(opts["--reps"]), opts["--seed"]))
    return 0


def cmd_prompt(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in LENS_TEXT:
        print(f"usage: rotation.py prompt <{'|'.join(LENS_TEXT)}>", file=sys.stderr)
        return 2
    print(prompt_for(argv[0]))
    print(f"\n--- do not paste this line. prompt_sha256 {prompt_hash(argv[0])} (lens: {argv[0]})", file=sys.stderr)
    return 0


def cmd_score(argv: list[str]) -> int:
    truth = None
    if "--truth" in argv:
        i = argv.index("--truth")
        truth = argv[i + 1]
        argv = argv[:i] + argv[i + 2 :]
    if len(argv) != 1:
        print("usage: rotation.py score sheet.csv [--truth peak]", file=sys.stderr)
        return 2
    with open(argv[0], newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    stale = [r["run"] for r in rows if r.get("prompt_sha256") and r.get("lens") in LENS_TEXT and r["prompt_sha256"] != prompt_hash(r["lens"])]
    if stale:
        print(f"warning: runs {', '.join(stale)} were made with a prompt that is not this file's prompt for that lens")
    print_score(score_sheet(rows), truth)
    return 0


def main(argv: list[str]) -> int:
    global VERBOSE
    if argv and argv[0] in ("plan", "prompt", "score"):
        return {"plan": cmd_plan, "prompt": cmd_prompt, "score": cmd_score}[argv[0]](argv[1:])
    VERBOSE = "-v" in argv
    for title, fn in (
        ("A. Thirteen hats: the arithmetic of a shared prior", section_a),
        ("B. What a rotation can and cannot identify", section_b),
        ("C. A toy: lenses as estimators, readers as noise", section_c),
        ("D. The pilot kit", section_d),
    ):
        print(title)
        fn()
    failed = [name for ok, name, _ in RESULTS if not ok]
    print(f"{len(RESULTS)} checks, {len(failed)} failed" + (": " + ", ".join(failed) if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
