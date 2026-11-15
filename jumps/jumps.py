#!/usr/bin/env python3
"""jumps.py: the program behind the notes "Where the jump goes".

The notes are about sentences that mention themselves, in logics with truth values
between false (0) and true (1). This program does not prove the notes. It recomputes
every number they mark [computed], and it tries the claims they mark [derived] on
examples, with a control beside each family of checks so that no check can pass by
being empty.

    python3 jumps.py        # every check, one line each
    python3 jumps.py -v     # the same, with the tables

Python 3, standard library only. No network, no files written. Exit status 0 when every
check passes, 1 otherwise. The random sentences in section D are drawn with SHA-256 in
counter mode, so they are the same on every machine.
"""
from __future__ import annotations

import hashlib
import math
import sys
import time
from fractions import Fraction as F

VERBOSE = "-v" in sys.argv[1:]
T0 = time.time()
RESULTS: list[tuple[str, bool]] = []


PENDING: list[str] = []


def check(tag: str, ok: bool, text: str) -> None:
    """Print one check, then whatever table lines were said for it."""
    RESULTS.append((tag, bool(ok)))
    print(f"{'ok  ' if ok else 'FAIL'} {tag:3} {text}")
    if VERBOSE:
        for ln in PENDING:
            print("         " + ln)
    PENDING.clear()


def say(*lines: str) -> None:
    """Table lines for the next check; shown only with -v."""
    PENDING.extend(lines)


def section(title: str) -> None:
    print("\n" + title)


# =====================================================================================
# A. Curry's sentence  C <-> (C -> A)  in three logics. Exact fractions.
#    Its value c must satisfy c = (c -> a), where a is the truth value of A.
# =====================================================================================
ONE, ZERO = F(1), F(0)


def imp_godel(x, y):      # Goedel-Dummett: jumps along the diagonal
    return ONE if x <= y else y


def imp_product(x, y):    # product logic: jumps only at (0, 0)
    return ONE if x <= y else y / x


def imp_luk(x, y):        # Lukasiewicz: continuous
    return min(ONE, 1 - x + y)


def grid(n):
    return [F(k, n) for k in range(n + 1)]


section("A. Curry's sentence C <-> (C -> A), exact")
G1600 = grid(1600)
A_VALUES = [F(0), F(1, 4), F(9, 16), F(1)]
curry = {name: {a: [c for c in G1600 if imp(c, a) == c] for a in A_VALUES}
         for name, imp in (("godel", imp_godel), ("product", imp_product))}
check("A1", all(curry["godel"][a] == [] for a in A_VALUES[:3]) and curry["godel"][ONE] == [ONE],
      "Goedel-Dummett: no value at a = 0, 1/4, 9/16; the value 1 at a = 1")
check("A2", curry["product"][ZERO] == [] and curry["product"][F(1, 4)] == [F(1, 2)]
      and curry["product"][F(9, 16)] == [F(3, 4)] and curry["product"][ONE] == [ONE],
      "product: the value sqrt(a) at a = 1/4, 9/16, 1; no value at a = 0 (the liar)")
G1200 = grid(1200)
ok = all([c for c in G1200 if imp_luk(c, a) == c] == [(1 + a) / 2] for a in grid(60))
check("A3", ok, "Lukasiewicz: exactly one value, (1 + a)/2, at each of 61 values of a (the liar sits at 1/2)")


def godel_closed(x, y):
    """The Goedel-Dummett -> with its graph closed: an interval of values on the diagonal."""
    if x < y:
        return (ONE, ONE)
    if x > y:
        return (y, y)
    return (y, ONE)


G240 = grid(240)
ok = True
for a in grid(24):
    got = [c for c in G240 if godel_closed(c, a)[0] <= c <= godel_closed(c, a)[1]]
    ok = ok and got == [a]
check("A4", ok, "close the graph of the Goedel-Dummett ->: Curry's sentence gets exactly one value, c = a (25 values of a)")

# =====================================================================================
# B. Lukasiewicz sentences that differ only in using one clause twice. Exact integers:
#    a truth value k/D is stored as the integer k, and the connectives keep that lattice.
#       x (+) y = min(1, x + y)      x (x) y = max(0, x + y - 1)      ~x = 1 - x
# =====================================================================================
def fibre(f, a, D):
    """All s in [0, 1] with f(s, a) = s, as a list of (lo, hi) fractions; a point has lo == hi.
    Exact when every breakpoint of f(., a) is a multiple of 1/D."""
    g = [f(s, a, D) - s for s in range(D + 1)]
    out = []
    for i in range(D):
        g0, g1 = g[i], g[i + 1]
        if g0 == 0 and g1 == 0:
            seg = (F(i, D), F(i + 1, D))
        elif g0 == 0:
            seg = (F(i, D), F(i, D))
        elif g1 == 0:
            seg = (F(i + 1, D), F(i + 1, D))
        elif (g0 > 0) != (g1 > 0):
            z = (i + F(g0, g0 - g1)) / D
            seg = (z, z)
        else:
            continue
        if out and out[-1][1] >= seg[0]:
            out[-1] = (out[-1][0], max(out[-1][1], seg[1]))
        else:
            out.append(seg)
    return out


def once(s, a, D):        # S <-> (S (+) A) (x) A
    return max(0, min(D, s + a) + a - D)


def twice(s, a, D):       # S <-> (S (+) A) (x) (S (+) A) (x) A
    return max(0, 2 * min(D, s + a) + a - 2 * D)


section("B. One clause used once or twice, in Lukasiewicz logic, exact")
D = 480
HALF, TWO3 = F(1, 2), F(2, 3)
ok1 = ok2 = True
for j in range(121):
    a = F(j, 120)
    k = j * 4
    want1 = [(ZERO, ZERO)] if a < HALF else ([(ZERO, HALF)] if a == HALF else [(a, a)])
    ok1 = ok1 and fibre(once, k, D) == want1
    pts = set()
    if a <= TWO3:
        pts.add(ZERO)
    if HALF <= a <= TWO3:
        pts.add(2 - 3 * a)
    if a >= HALF:
        pts.add(a)
    got = fibre(twice, k, D)
    ok2 = ok2 and all(lo == hi for lo, hi in got) and {lo for lo, _ in got} == pts
check("B1", ok1, "used once: S = 0 below a = 1/2, S = a above, and every value in [0, 1/2] at a = 1/2 exactly (121 values of a)")
check("B2", ok2, "used twice: S = 0 up to a = 2/3, S = a from a = 1/2, and 2 - 3a between them (121 values of a)")

low = {j: min(lo for lo, _ in fibre(twice, 4 * j, D)) for j in (80, 81)}
high = {j: max(hi for _, hi in fibre(twice, 4 * j, D)) for j in (59, 60)}
ok = (low[80] == 0 and low[81] == F(81, 120) and high[60] == HALF and high[59] == 0
      and len(fibre(twice, 4 * 70, D)) == 3)
say("three values at a = 7/12: " + ", ".join(str(lo) for lo, _ in fibre(twice, 280, D)))
check("B3", ok, "used twice: raising A, S leaps from 0 to 2/3 at a = 2/3; lowering A, it drops from 1/2 to 0 at a = 1/2")


def enumerate_terms(depth):
    """All terms from s, a with ~, (+), (x), built in rounds, at most two mentions of s.
    Each term is (name, function, mentions of s, set of signs under which s occurs)."""
    terms = [("s", lambda s, a, D: s, 1, frozenset([1])), ("a", lambda s, a, D: a, 0, frozenset())]
    for _ in range(depth):
        new = []
        for n1, f1, k1, p1 in terms:
            new.append((f"~{n1}", (lambda f1: lambda s, a, D: D - f1(s, a, D))(f1), k1, frozenset(-x for x in p1)))
        for n1, f1, k1, p1 in terms:
            for n2, f2, k2, p2 in terms:
                if k1 + k2 > 2:
                    continue
                new.append((f"({n1}+{n2})", (lambda f1, f2: lambda s, a, D: min(D, f1(s, a, D) + f2(s, a, D)))(f1, f2),
                            k1 + k2, p1 | p2))
                new.append((f"({n1}*{n2})", (lambda f1, f2: lambda s, a, D: max(0, f1(s, a, D) + f2(s, a, D) - D))(f1, f2),
                            k1 + k2, p1 | p2))
        seen = {t[0] for t in terms}
        for t in new:
            if t[0] not in seen:
                seen.add(t[0])
                terms.append(t)
    return terms


TERMS = enumerate_terms(2)
D2 = 144
one = [t for t in TERMS if t[2] == 1]
two = [t for t in TERMS if t[2] == 2]
split = sum(1 for _, f, _, _ in one for j in range(13) if len(fibre(f, 12 * j, D2)) != 1)
check("B4", split == 0, f"one self-mention: the values at each a form a single interval or point ({len(one)} sentences, 13 values of a)")
folded = [n for n, f, _, _ in two if max(len(fibre(f, 12 * j, D2)) for j in range(13)) >= 3]
say("for example: " + ", ".join(folded[:4]))
check("B5", len(folded) > 0, f"control, two self-mentions: {len(folded)} of {len(two)} sentences have three or more separate values at some a")
liars = [t for t in TERMS if t[2] >= 1 and t[3] == frozenset([-1])]
bad = sum(1 for _, f, _, _ in liars for j in range(13)
          if not (len(fibre(f, 12 * j, D2)) == 1 and fibre(f, 12 * j, D2)[0][0] == fibre(f, 12 * j, D2)[0][1]))
check("B6", bad == 0, f"liar-type (S only under an odd number of negations): exactly one value at every a ({len(liars)} sentences)")

# =====================================================================================
# C. The latch. Floats. Six conditionals that obey both laws, and two that drop one.
#       L1: if x <= y then (x -> y) = 1          L2: (1 -> 0) = 0
#    not Y  is  Y -> 0.    X = not (S -> B).    Q = (not X -> X).
#    with min, max:  S <-> (Q v D) ^ E          with -> alone:  S <-> (not D -> Q)
# =====================================================================================
class Draw:
    """SHA-256 in counter mode: the same numbers on every machine."""

    def __init__(self, seed):
        self.seed, self.i = seed.encode(), 0

    def unit(self):
        h = hashlib.sha256(self.seed + str(self.i).encode()).digest()
        self.i += 1
        return int.from_bytes(h[:8], "big") / 2.0 ** 64

    def pick(self, seq):
        return seq[int(self.unit() * len(seq))]


def clip(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def c_luk(x, y):
    return min(1.0, 1.0 - x + y)


def c_pow(p):
    def cond(x, y):
        if x <= y or y >= 1.0:
            return 1.0
        return y + (1.0 - y) * ((1.0 - x) / (1.0 - y)) ** p
    return cond


def c_sq(x, y):
    return 1.0 if x <= y else 1.0 - (x - y) ** 2


def c_wob(x, y):          # not monotone in either argument
    return 1.0 if x <= y else clip(1.0 - (x - y) * (1.0 + 0.3 * math.sin(7 * x + 3 * y)))


def c_gen(x, y):          # fully true even a little above the diagonal
    return 1.0 if x <= y + 0.1 else clip(1.0 - (x - y - 0.1) / 0.9)


def c_half(x, y):         # keeps L1, drops L2: (1 -> 0) = 1/2
    return min(1.0, 1.0 - (x - y) / 2.0)


def c_avg(x, y):          # keeps L2, drops L1: (x -> x) = 1/2
    return (1.0 - x + y) / 2.0


SHARP = [("Lukasiewicz", c_luk), ("power 2", c_pow(2.0)), ("power 1/2", c_pow(0.5)),
         ("1 - (x-y)^2", c_sq), ("wobbly", c_wob), ("generous", c_gen)]
BLUNT = [("half-slope", c_half), ("averaging", c_avg)]


def laws(cond, n=60):
    l1 = all(cond(i / n, j / n) == 1.0 for i in range(n + 1) for j in range(i, n + 1))
    return l1, cond(1.0, 0.0) == 0.0


def make_q(cond, b):
    def q(s):
        x = cond(cond(s, b), 0.0)             # X = not (S -> B)
        return cond(cond(x, 0.0), x)          # not X -> X
    return q


def settle(f, s, cap=20000, tol=1e-13):
    """Let S settle: apply the sentence to its own value until nothing changes."""
    for _ in range(cap):
        t = f(s)
        if abs(t - s) <= tol:
            return t
        s = t
    return s


def run_latch(cond, b0, with_minmax, steps=400):
    """reset -> hold -> set -> hold. Returns S at hold after reset, S at set, S at hold after set,
    and the largest single change on the way up with the D at which it happened."""
    neg = lambda x: cond(x, 0.0)
    if with_minmax:
        q = make_q(cond, b0)
        f = lambda d, e: (lambda s: min(max(q(s), d), e))
        s = settle(f(0.0, 0.0), 0.0)
        for k in range(1, 101):                       # restore E
            s = settle(f(0.0, k / 100), s)
        up = lambda d: f(d, 1.0)
    else:
        f = lambda b, d: (lambda s, q=make_q(cond, b), nd=neg(d): cond(nd, q(s)))
        s = settle(f(1.0, 0.0), 0.0)
        for k in range(1, 101):                       # slide B from true down to b0
            s = settle(f((1.0 - k / 100) + b0 * k / 100, 0.0), s)
        up = lambda d: f(b0, d)
    after_reset = s
    leap, where = 0.0, None
    for k in range(1, steps + 1):                     # raise D
        t = settle(up(k / steps), s)
        if abs(t - s) > leap:
            leap, where = abs(t - s), k / steps
        s = t
    at_set = s
    for k in range(steps - 1, -1, -1):                # lower D again
        s = settle(up(k / steps), s)
    return after_reset, at_set, s, leap, where


section("C. The latch, in six logics that obey L1 and L2 and two that drop one")
ok = all(laws(c) == (True, True) for _, c in SHARP) and laws(c_half) == (True, False) and laws(c_avg) == (False, True)
check("C1", ok, "the six conditionals obey L1 and L2; half-slope drops only L2, averaging drops only L1")

B0 = 0.3
GRID = [i / 2000 for i in range(2001)]
ok = True
for name, cond in SHARP:
    q = make_q(cond, B0)
    flat = max(abs(q(s)) for s in GRID if s <= B0)
    top = min(s for s in GRID if all(q(u) == 1.0 for u in GRID if u >= s))
    ok = ok and flat == 0.0 and top < 1.0
    say(f"{name:12} Q = 0 on [0, {B0}];  Q = 1 on [{top:.4f}, 1]")
check("C2", ok, "in all six, Q is exactly 0 for S <= B and exactly 1 on a whole stretch below S = 1 (B = 0.3)")

for tag, with_minmax, label in (("C3", True, "S <-> (Q v D) ^ E"), ("C4", False, "S <-> (not D -> Q), with -> alone")):
    ok = True
    for name, cond in SHARP:
        r, top, h, leap, where = run_latch(cond, B0, with_minmax)
        ok = ok and r == 0.0 and top == 1.0 and h == 1.0 and leap > 0.2
        say(f"{name:12} hold after reset {r:.3f}   hold after set {h:.3f}   leap of {leap:.3f} at D = {where:.4f}")
    check(tag, ok, f"{label}: in all six, S reads 0 at the hold world after reset and 1 after set, with a leap between")

ok = True
for name, cond in BLUNT:
    for with_minmax in (True, False):
        r, top, h, leap, where = run_latch(cond, B0, with_minmax)
        ok = ok and abs(r - h) < 1e-9 and leap < 0.01
        say(f"{name:12} {'min/max' if with_minmax else '-> alone':8} hold after reset {r:.6f}   hold after set {h:.6f}   largest step {leap:.4f}")
check("C5", ok, "control, the two blunt conditionals: the same sentences read the same after reset and after set, and never leap")


# ---- the amplifier criterion: with min and max, any g that is below the diagonal at p
#      and above it at a later q gives a latch  S <-> (g(S) v D) ^ E.
def roots(f, n=1000):
    """All s with f(s) = s, by scanning for sign changes and bisecting."""
    out = []
    ps, ph = 0.0, f(0.0)
    if ph == 0.0:
        out.append(0.0)
    for i in range(1, n + 1):
        s = i / n
        h = f(s) - s
        if h == 0.0:
            out.append(s)
        elif ph != 0.0 and (h > 0) != (ph > 0):
            lo, hi = ps, s
            for _ in range(50):
                mid = (lo + hi) / 2
                if (f(mid) - mid > 0) == (ph > 0):
                    lo = mid
                else:
                    hi = mid
            out.append((lo + hi) / 2)
        ps, ph = s, h
    return out


def nearest(f, s):
    return min(roots(f), key=lambda r: abs(r - s))


def amplifier_run(g, p, steps=100, follow=settle):
    """From the world (D, E) = (p, p), where S = p is forced: raise E to 1, raise D to 1,
    lower D back to p. Returns S at (p, 1) on the way out and on the way back."""
    f = lambda d, e: (lambda s: min(max(g(s), d), e))
    between = lambda t: (1.0 - t) * p + t           # p at t = 0, exactly 1 at t = 1
    s = follow(f(p, p), p)
    for k in range(1, 21):
        s = follow(f(p, between(k / 20)), s)
    out = s
    for k in range(1, steps + 1):
        s = follow(f(between(k / steps), 1.0), s)
    top = s
    for k in range(steps - 1, -1, -1):
        s = follow(f(between(k / steps), 1.0), s)
    return out, top, s


def piecewise(ys):
    """The piecewise-linear function through (0, y0), (0.2, y1), ..., (1, y5)."""
    def g(s):
        i = min(int(s * 5), 4)
        t = s * 5 - i
        return ys[i] * (1 - t) + ys[i + 1] * t
    return g


rng = Draw("amplifiers")
amps = []
while len(amps) < 100:                                # rising g with an upward crossing
    g = piecewise(sorted(rng.unit() for _ in range(6)))
    below = [i / 100 for i in range(1, 100) if g(i / 100) < i / 100 - 0.02]
    if not below:
        continue
    above = [i / 100 for i in range(1, 100) if i / 100 > below[0] and g(i / 100) > i / 100 + 0.02]
    if above:
        amps.append((g, below[0], above[-1]))
ok = True
for g, p, q in amps:
    out, top, back = amplifier_run(g, p)
    ok = ok and abs(out - p) < 1e-9 and top == 1.0 and back > q
check("C6", ok, "amplifier criterion: 100 random rising g that cross the diagonal upward all give a latch (S = p one way, S > q the other)")

ok = True
for _ in range(100):                                  # control: slopes at most 0.9, so no upward crossing
    y = [0.1 * rng.unit()]
    for _ in range(5):
        y.append(y[-1] + 0.2 * 0.9 * rng.unit())
    out, top, back = amplifier_run(piecewise(y), 0.3)
    ok = ok and abs(out - back) < 1e-9
check("C7", ok, "control: 100 random g with slopes at most 0.9 read the same on the way out and on the way back")


def bicond(x, y):         # 1 - |x - y|: (x -> x) = 1 and (1 -> 0) = 0, but (0 -> 1) = 0, so L1 fails
    return 1 - abs(x - y)


g_b = lambda s: bicond(F(1, 4), bicond(s, bicond(s, ZERO)))
exact = (g_b(F(7, 10)) == F(13, 20) and g_b(F(17, 20)) == F(19, 20)
         and bicond(ZERO, ONE) == ZERO and bicond(ONE, ZERO) == ZERO and bicond(HALF, HALF) == ONE)
g_bf = lambda s: 1.0 - abs(0.25 - (1.0 - abs(s - (1.0 - abs(s - 0.0)))))
out, top, back = amplifier_run(g_bf, 0.7, follow=nearest)
say(f"biconditional: g(7/10) = 13/20, g(17/20) = 19/20;  S = {out:.4f} on the way out, {back:.4f} on the way back")
check("C8", exact and abs(out - 0.7) < 1e-9 and top == 1.0 and back > 0.85,
      "L1 is not needed for an amplifier: 1 - |x - y| breaks L1, and g(s) = (1/4 <-> (s <-> (s <-> 0))) still gives a latch")

# =====================================================================================
# D. Blunt conditionals have no jump. Random sentences S <-> phi(S, A) from ->, min, max.
#    "Jump" here: the least solution, as a function of a, has a gap of more than 0.04
#    that survives 30 halvings of the interval around it.
# =====================================================================================
def sentence(rng, depth):
    """A random sentence as a nested tuple: a leaf "s", "a", "0", "1", or (op, left, right)."""
    if depth == 0 or rng.unit() < 0.22:
        return rng.pick(["s", "a", "a", "0", "1"])
    op = rng.pick(["->", "->", "min", "max"])
    left = sentence(rng, depth - 1)
    return (op, left, sentence(rng, depth - 1))


def leaves(t):
    return {t} if isinstance(t, str) else leaves(t[1]) | leaves(t[2])


def show(t):
    if isinstance(t, str):
        return t
    op, x, y = t
    return f"({show(x)} -> {show(y)})" if op == "->" else f"{op}({show(x)}, {show(y)})"


def as_function(t, cond):
    """The sentence as a function of (s, a), built from closures; no code is made from text."""
    if t == "s":
        return lambda s, a: s
    if t == "a":
        return lambda s, a: a
    if t in ("0", "1"):
        return (lambda v: lambda s, a: v)(float(t))
    op, x, y = t
    fx, fy = as_function(x, cond), as_function(y, cond)
    if op == "->":
        return lambda s, a: cond(fx(s, a), fy(s, a))
    if op == "min":
        return lambda s, a: min(fx(s, a), fy(s, a))
    return lambda s, a: max(fx(s, a), fy(s, a))


def least(f, a, n=200):
    """The least s with f(s, a) = s."""
    if f(0.0, a) <= 1e-15:
        return 0.0
    prev = 0.0
    for i in range(1, n + 1):
        s = i / n
        if f(s, a) - s <= 0.0:
            lo, hi = prev, s
            for _ in range(40):
                mid = (lo + hi) / 2
                if f(mid, a) - mid > 0.0:
                    lo = mid
                else:
                    hi = mid
            return hi
        prev = s
    return 1.0


def worst_gap(f, na=60, suspect=0.05):
    ls = [least(f, j / na) for j in range(na + 1)]
    worst = 0.0
    for j in range(na):
        if abs(ls[j + 1] - ls[j]) > suspect:
            lo, hi, llo, lhi = j / na, (j + 1) / na, ls[j], ls[j + 1]
            for _ in range(30):
                mid = (lo + hi) / 2
                lm = least(f, mid)
                if abs(lm - llo) >= abs(lhi - lm):
                    hi, lhi = mid, lm
                else:
                    lo, llo = mid, lm
            worst = max(worst, abs(lhi - llo))
    return worst


section("D. Random sentences from ->, min, max: does the least solution jump?")
rng = Draw("where the jump goes")
SENTENCES = []
while len(SENTENCES) < 200:
    t = sentence(rng, 3)
    if {"s", "a"} <= leaves(t) and t not in SENTENCES:
        SENTENCES.append(t)
counts, example = {}, {}
for name, cond in (("half-slope", c_half), ("averaging", c_avg), ("Lukasiewicz", c_luk)):
    hits = [t for t in SENTENCES if worst_gap(as_function(t, cond)) > 0.04]
    counts[name], example[name] = len(hits), (show(hits[0]) if hits else None)
check("D1", counts["half-slope"] == 0, f"half-slope ->: {counts['half-slope']} of {len(SENTENCES)} sentences jump")
check("D2", counts["averaging"] == 0, f"averaging ->: {counts['averaging']} of {len(SENTENCES)} sentences jump")
say(f"for example S <-> {example['Lukasiewicz']}")
check("D3", counts["Lukasiewicz"] > 0, f"control, Lukasiewicz ->: {counts['Lukasiewicz']} of the same {len(SENTENCES)} sentences jump")

# =====================================================================================
# E. Truth values that do not form a line: pairs (x1, x2), ordered coordinate by
#    coordinate. A conditional whose two output coordinates differ, obeying L1 and L2.
# =====================================================================================
O2, I2 = (0.0, 0.0), (1.0, 1.0)


def leq2(x, y):
    return x[0] <= y[0] and x[1] <= y[1]


def c_square(x, y):
    if leq2(x, y):
        return I2
    d = max(x[0] - y[0], x[1] - y[1])
    return (clip(1.0 - d * (1.0 + 0.3 * math.sin(7 * x[0] + 3 * y[1]))),
            clip(1.0 - d * (1.0 + 0.3 * math.sin(5 * x[1] + 2 * y[0] + 2.0))))


def c_square_half(x, y):  # coordinatewise half-slope: keeps L1, drops L2
    return (c_half(x[0], y[0]), c_half(x[1], y[1]))


def make_q2(cond, b):
    def q(s):
        x = cond(cond(s, b), O2)
        return cond(cond(x, O2), x)
    return q


def settle2(f, s, cap=5000, tol=1e-13):
    for _ in range(cap):
        t = f(s)
        if max(abs(t[0] - s[0]), abs(t[1] - s[1])) <= tol:
            return t
        s = t
    return s


def run_latch2(cond, b0, steps=200):
    neg = lambda x: cond(x, O2)
    f = lambda b, d: (lambda s, q=make_q2(cond, b), nd=neg(d): cond(nd, q(s)))
    s = settle2(f(I2, O2), O2)
    for k in range(1, 101):                           # slide B from (1, 1) down to b0
        t = k / 100
        s = settle2(f(((1.0 - t) + b0[0] * t, (1.0 - t) + b0[1] * t), O2), s)
    after_reset = s
    for k in range(1, steps + 1):                     # raise D along the curve (t, t^2)
        t = k / steps
        s = settle2(f(b0, (t, t * t)), s)
    at_set = s
    for k in range(steps - 1, -1, -1):
        t = k / steps
        s = settle2(f(b0, (t, t * t)), s)
    return after_reset, at_set, s


section("E. Pairs of truth values, with a conditional that mixes the two coordinates")
B2 = (0.2, 0.2)
q2 = make_q2(c_square, B2)
n = 40
off_diagonal = max(abs(v[0] - v[1]) for v in (c_square((i / n, j / n), (k / n, m / n))
                                               for i in range(0, n + 1, 4) for j in range(0, n + 1, 4)
                                               for k in range(0, n + 1, 4) for m in range(0, n + 1, 4)))
l1 = all(c_square((i / n, j / n), (k / n, m / n)) == I2
         for i in range(0, n + 1, 4) for j in range(0, n + 1, 4)
         for k in range(i, n + 1, 4) for m in range(j, n + 1, 4))
check("E1", l1 and c_square(I2, O2) == O2 and off_diagonal > 0.1,
      f"the conditional obeys L1 and L2 and is not coordinatewise (its two outputs differ by up to {off_diagonal:.2f})")
ok = all(q2((0.2 * i / n, 0.2 * j / n)) == O2 for i in range(n + 1) for j in range(n + 1))
check("E2", ok, "Q is exactly (0, 0) for every S below B = (0.2, 0.2)")
width = 0.0
for w in (0.30, 0.25, 0.20, 0.15, 0.10, 0.05, 0.02):
    if all(q2((1.0 - w * i / n, 1.0 - w * j / n)) == I2 for i in range(n + 1) for j in range(n + 1)):
        width = w
        break
check("E3", width > 0.0, f"Q is exactly (1, 1) on the whole square of side {width:.2f} below (1, 1)")
r, top, h = run_latch2(c_square, B2)
check("E4", r == O2 and top == I2 and h == I2,
      "S <-> (not D -> Q): S reads (0, 0) at the hold world after reset and (1, 1) after set")
r, top, h = run_latch2(c_square_half, B2)
say(f"half-slope on the square: hold after reset ({r[0]:.6f}, {r[1]:.6f}), after set ({h[0]:.6f}, {h[1]:.6f})")
check("E5", max(abs(r[0] - h[0]), abs(r[1] - h[1])) < 1e-9,
      "control, coordinatewise half-slope: the same sentence reads the same after reset and after set")

# =====================================================================================
# F. Quantifiers. In Lukasiewicz logic "not R, n times over" (n-fold (+)) has the value
#    min(1, n(1 - r)). The sentence  R <-> "for some n: not R, n times over"  takes the
#    supremum over n. Exact fractions.
# =====================================================================================
section("F. A quantifier over repetitions")
ok = True
for N in range(1, 201):
    r = F(N, N + 1)
    eps = F(1, 10 ** 6)
    ok = ok and min(ONE, N * (1 - r)) == r
    ok = ok and min(ONE, N * (1 - (r - eps))) > r - eps and min(ONE, N * (1 - (r + eps))) < r + eps
check("F1", ok, "stop at N repetitions and the sentence has the single value N/(N + 1), for N = 1 to 200")
ok = True
for k in range(1000):
    r = F(k, 1000)
    n = math.ceil(1 / (1 - r))
    ok = ok and min(ONE, n * (1 - r)) == ONE          # so the supremum is 1, which is not r
ok = ok and all(min(ONE, n * (1 - ONE)) == ZERO for n in range(1, 1000))   # at r = 1 it is 0
check("F2", ok, "with no stop, the supremum is 1 for every r < 1 and 0 at r = 1: the sentence has no value at all")

# =====================================================================================
failed = [tag for tag, good in RESULTS if not good]
print(f"\n{len(RESULTS)} checks, {len(failed)} failed, {time.time() - T0:.1f} seconds"
      + ("" if not failed else "   FAILED: " + " ".join(failed)))
sys.exit(1 if failed else 0)
