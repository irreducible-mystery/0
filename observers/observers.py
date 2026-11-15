#!/usr/bin/env python3
"""observers.py - every computed number in "Sameness on a budget", reproduced.

The notes this file ships with propose a mathematics in which "equal" means
"no test this observer can afford tells them apart". This program does not
prove the notes. It does two smaller things:

  1. recomputes every number the notes mark [computed], and
  2. checks the laws the notes mark [derived] on examples and on random
     finite models, with a negative control beside each law so that a check
     cannot pass by being empty.

Usage:
    python3 observers.py          # run everything (a few seconds)
    python3 observers.py -v       # also print the tables

Standard library only. No network, no files written. Exit status 0 if every
check passes, 1 otherwise. Randomness comes from SHA-256 in counter mode, so
the numbers are the same on every machine and Python version; the one
exception is section F, which uses zlib and therefore asserts only bounds.
"""
from __future__ import annotations

import hashlib
import heapq
import math
import sys
import zlib
from fractions import Fraction
from itertools import combinations

VERBOSE = "-v" in sys.argv[1:]
RESULTS: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str) -> None:
    RESULTS.append((bool(ok), name, detail))
    print(("ok   " if ok else "FAIL ") + name + "  " + detail)


def say(text: str = "") -> None:
    if VERBOSE:
        print(text)


class Rng:
    """Deterministic, portable randomness: SHA-256 of (seed, counter)."""

    def __init__(self, seed: str) -> None:
        self.seed = seed.encode()
        self.n = 0

    def _block(self) -> bytes:
        self.n += 1
        return hashlib.sha256(self.seed + b":" + str(self.n).encode()).digest()

    def below(self, k: int) -> int:
        """Uniform integer in [0, k). Rejection sampling, so no modulo bias."""
        if k <= 1:
            return 0
        bits = (k - 1).bit_length()
        while True:
            v = int.from_bytes(self._block()[:8], "big") >> (64 - bits)
            if v < k:
                return v

    def bytes(self, n: int) -> bytes:
        out = b""
        while len(out) < n:
            out += self._block()
        return out[:n]


# --------------------------------------------------------------------------
# A. Coins: sameness as a curve
# --------------------------------------------------------------------------
# Objects: coins. A test with budget n flips the coin n times and answers yes
# or no by any rule. The largest gap such a test can show between two coins is
# the total variation distance between Bin(n, p) and Bin(n, q); the head count
# is a sufficient statistic, so nothing is lost by looking only at it.


def _weights(n: int, p: float, lo: int, hi: int) -> list[float]:
    """Binomial(n, p) probabilities for k in [lo, hi], normalised on that window.

    Built outward from the mode by the ratio P(k+1)/P(k) = (n-k)/(k+1) * p/(1-p),
    which avoids subtracting huge log-gamma values from each other.
    """
    mode = min(max(int(round(n * p)), lo), hi)
    w = [0.0] * (hi - lo + 1)
    w[mode - lo] = 1.0
    r = p / (1.0 - p)
    for k in range(mode, hi):
        w[k + 1 - lo] = w[k - lo] * (n - k) / (k + 1) * r
    for k in range(mode, lo, -1):
        w[k - 1 - lo] = w[k - lo] * k / (n - k + 1) / r
    total = math.fsum(w)
    return [x / total for x in w]


def tv_coins(n: int, p: float, q: float, full: bool = False) -> float:
    """Total variation distance between Bin(n, p) and Bin(n, q).

    Unless full=True the sum runs over a window that leaves out less than
    1e-30 of either distribution (12 standard deviations past both means).
    """
    if full:
        lo, hi = 0, n
    else:
        pad = int(6 * math.sqrt(n)) + 5  # 6*sqrt(n) >= 12 standard deviations
        lo = max(0, int(n * min(p, q)) - pad)
        hi = min(n, int(n * max(p, q)) + pad)
    a = _weights(n, p, lo, hi)
    b = _weights(n, q, lo, hi)
    return 0.5 * math.fsum(abs(x - y) for x, y in zip(a, b))


def price(p: float, q: float, target: float = 0.5) -> int:
    """Fewest flips at which the best test's edge reaches target.

    Bisection is valid because the edge cannot fall as flips are added: an
    observer with n+1 flips may ignore one of them (checked in A3).
    """
    hi = 1
    while tv_coins(hi, p, q) < target:
        hi *= 2
    lo = hi // 2
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if tv_coins(mid, p, q) >= target:
            hi = mid
        else:
            lo = mid
    return hi


def section_a() -> None:
    pairs = [(0.5, 0.6), (0.5, 0.51), (0.5, 0.501)]
    ns = [10, 100, 1000, 10_000, 100_000, 1_000_000]
    expected = {
        (0.5, 0.6): [0.2562, 0.6855, 0.9986, 1.0, 1.0, 1.0],
        (0.5, 0.51): [0.0248, 0.0799, 0.2481, 0.6827, 0.9984, 1.0],
        (0.5, 0.501): [0.0025, 0.0080, 0.0252, 0.0797, 0.2482, 0.6827],
    }
    ok = True
    say("  flips      " + "".join(f"{n:>11,}" for n in ns))
    for pq in pairs:
        row = [round(tv_coins(n, *pq), 4) for n in ns]
        ok = ok and row == expected[pq]
        say(f"  {pq[0]:.3f} vs {pq[1]:.3f}" + "".join(f"{v:>11.4f}" for v in row))
    check("A1", ok, "edge of the best test at 10..1,000,000 flips matches the table in the notes")

    worst = max(
        abs(tv_coins(n, p, q) - tv_coins(n, p, q, full=True))
        for (p, q) in pairs
        for n in (10, 100, 1000, 20_000)
    )
    check("A2", worst < 1e-12, f"windowed sum equals the full sum (largest difference {worst:.1e})")

    seq = [tv_coins(n, 0.5, 0.6, full=True) for n in range(1, 301)]
    drops = sum(1 for a, b in zip(seq, seq[1:]) if b < a - 1e-12)
    check("A3", drops == 0, "law 1 on coins: the edge never falls as flips are added, n = 1..300")

    found = [price(p, q) for (p, q) in pairs]
    margins = []
    for (p, q), n in zip(pairs, found):
        margins.append((tv_coins(n, p, q) - 0.5, 0.5 - tv_coins(n - 1, p, q)))
    clear = all(up > 1e-9 and down > 1e-9 for up, down in margins)
    check(
        "A4",
        found == [45, 4549, 454936] and clear,
        "flips needed to be right three times in four: "
        + ", ".join(f"{n:,}" for n in found)
        + f"  (ratios {found[1] / found[0]:.1f} and {found[2] / found[1]:.1f})",
    )
    say("  margins above/below one half at each price: " + ", ".join(f"{u:.1e}/{d:.1e}" for u, d in margins))

    n = 100
    ab, bc, ac = tv_coins(n, 0.5, 0.55), tv_coins(n, 0.55, 0.6), tv_coins(n, 0.5, 0.6)
    check(
        "A5",
        ac <= ab + bc + 1e-12 and ac > max(ab, bc),
        f"law 2 on coins at 100 flips: {ac:.4f} <= {ab:.4f} + {bc:.4f}, and the chain leaks ({ac:.4f} > {max(ab, bc):.4f})",
    )


# --------------------------------------------------------------------------
# B. Parity: computing can create distinctions
# --------------------------------------------------------------------------
# Objects: two random sources of N-bit strings, one uniform over strings with
# an even number of 1s, one uniform over strings with an odd number. A test
# with budget b reads at most b of the N bits.

N_BITS = 6


def popcount(x: int) -> int:
    return bin(x).count("1")


def marginal(dist: dict[int, Fraction], mask: int) -> dict[int, Fraction]:
    out: dict[int, Fraction] = {}
    for x, pr in dist.items():
        out[x & mask] = out.get(x & mask, Fraction(0)) + pr
    return out


def tv_exact(a: dict[int, Fraction], b: dict[int, Fraction]) -> Fraction:
    keys = set(a) | set(b)
    return sum((abs(a.get(k, Fraction(0)) - b.get(k, Fraction(0))) for k in keys), Fraction(0)) / 2


def read_budget_profile(a: dict[int, Fraction], b: dict[int, Fraction], nbits: int) -> list[Fraction]:
    """Largest edge of a test that reads at most k chosen bits, for k = 0..nbits."""
    prof = []
    best = Fraction(0)
    for k in range(nbits + 1):
        for positions in combinations(range(nbits), k):
            mask = sum(1 << i for i in positions)
            best = max(best, tv_exact(marginal(a, mask), marginal(b, mask)))
        prof.append(best)
    return prof


def walsh(g: list[Fraction]) -> list[Fraction]:
    """Fourier (Walsh) coefficients of g on {0,1}^n, n = log2(len(g))."""
    size = len(g)
    return [
        sum((g[x] * (-1 if popcount(x & s) % 2 else 1) for x in range(size)), Fraction(0)) / size
        for s in range(size)
    ]


def section_b() -> None:
    size = 1 << N_BITS
    even = {x: Fraction(1, size // 2) for x in range(size) if popcount(x) % 2 == 0}
    odd = {x: Fraction(1, size // 2) for x in range(size) if popcount(x) % 2 == 1}
    prof = read_budget_profile(even, odd, N_BITS)
    say("  bits read:  " + " ".join(str(k) for k in range(N_BITS + 1)))
    say("  best edge:  " + " ".join(str(v) for v in prof))
    check(
        "B1",
        prof == [Fraction(0)] * N_BITS + [Fraction(1)],
        f"even- and odd-parity strings of {N_BITS} bits: edge 0 for every test reading fewer than {N_BITS} bits, 1 at {N_BITS}",
    )

    # f = "compute the parity", cost N_BITS reads. Its output is one bit.
    f_even = {0: Fraction(1)}
    f_odd = {1: Fraction(1)}
    after = read_budget_profile(f_even, f_odd, 1)
    check("B2", after[1] == 1, "after someone computes the parity, a test reading one bit separates them completely")

    b = 1
    lhs = after[b]  # d_b(f(x), f(y))
    rhs = Fraction(1)  # d_{b + cost(f)}(x, y): budget above N_BITS reads everything
    check(
        "B3",
        lhs <= rhs and lhs > prof[b],
        f"law 3 holds with its budget shift (1 <= 1) and fails without it: at budget {b}, {lhs} after computing > {prof[b]} before",
    )

    diff = [even.get(x, Fraction(0)) - odd.get(x, Fraction(0)) for x in range(size)]
    coeffs = walsh(diff)
    support = [s for s, c in enumerate(coeffs) if c != 0]
    check(
        "B4",
        support == [size - 1],
        "Fourier view: the difference between the two sources has all its weight on the one pattern that involves every bit",
    )

    rng = Rng("parseval")
    f = [Fraction(rng.below(2001) - 1000, 1000) for _ in range(size)]
    lhs2 = sum((c * c for c in walsh(f)), Fraction(0))
    rhs2 = sum((v * v for v in f), Fraction(0)) / size
    levels = [Fraction(0)] * (N_BITS + 1)
    for s, c in enumerate(walsh(f)):
        levels[popcount(s)] += c * c
    check(
        "B5",
        lhs2 == rhs2 and sum(levels, Fraction(0)) == rhs2,
        "Parseval, exactly: the weights at levels 0..6 of a random function add up to the whole",
    )


# --------------------------------------------------------------------------
# C. Several observers at once
# --------------------------------------------------------------------------


def classes(view) -> int:
    return len(set(view))


def section_c() -> None:
    xs = range(100)
    joint = {(x % 4, x % 25) for x in xs}
    check(
        "C1",
        len(joint) == 100 and 37 % 4 == 41 % 4 and 37 % 25 == 62 % 25 and 37 % 25 != 41 % 25 and 37 % 4 != 62 % 4,
        "0..99 seen mod 4 and mod 25: 100 distinct joint views; 37 and 41 agree mod 4, 37 and 62 agree mod 25",
    )
    waste = {(x % 10, x % 20) for x in xs}
    check("C2", len(waste) == 20, "mod 10 with mod 20 promises 10 * 20 = 200 distinctions and delivers 20")

    rng = Rng("law4")
    bad = 0
    equal = 0
    for _ in range(1000):
        n = 2 + rng.below(40)
        a = [rng.below(1 + rng.below(6)) for _ in range(n)]
        b = [rng.below(1 + rng.below(6)) for _ in range(n)]
        j = classes(zip(a, b))
        if j > classes(a) * classes(b):
            bad += 1
        if j == classes(a) * classes(b):
            equal += 1
    check("C3", bad == 0, f"law 4 on 1000 random pairs of observers: joint classes never exceed the product (equal in {equal})")

    ok = True
    for a in range(2, 13):
        for b in range(2, 13):
            j = len({(x % a, x % b) for x in range(a * b)})
            lcm = a * b // math.gcd(a, b)
            ok = ok and j == lcm and ((j == a * b) == (math.gcd(a, b) == 1))
    check("C4", ok, "remainder observers mod a and mod b, 2..12: joint classes = lcm(a, b), equal to a*b exactly when coprime")

    def entropy(view) -> float:
        counts: dict = {}
        total = 0
        for v in view:
            counts[v] = counts.get(v, 0) + 1
            total += 1
        return -sum(c / total * math.log2(c / total) for c in counts.values())

    worst = 0.0
    for _ in range(500):
        n = 2 + rng.below(60)
        a = [rng.below(4) for _ in range(n)]
        b = [rng.below(4) for _ in range(n)]
        worst = max(worst, entropy(zip(a, b)) - entropy(a) - entropy(b))
    check("C5", worst < 1e-9, "law 4 in entropy form on 500 random pairs: H(joint) <= H(A) + H(B)")


# --------------------------------------------------------------------------
# D. Primes as observers
# --------------------------------------------------------------------------


def factor(n: int) -> dict[int, int]:
    out: dict[int, int] = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            out[d] = out.get(d, 0) + 1
            n //= d
        d += 1 if d == 2 else 2
    if n > 1:
        out[n] = out.get(n, 0) + 1
    return out


def size_p(x: Fraction, p: int) -> Fraction:
    """The p-observer's size of a nonzero fraction: p ** -(times p divides x)."""
    v = 0
    a, b = abs(x.numerator), x.denominator
    while a % p == 0:
        a //= p
        v += 1
    while b % p == 0:
        b //= p
        v -= 1
    return Fraction(p) ** (-v)


def product_over_observers(x: Fraction) -> Fraction:
    primes = set(factor(abs(x.numerator))) | set(factor(x.denominator))
    out = abs(x)
    for p in primes:
        out *= size_p(x, p)
    return out


def section_d() -> None:
    check(
        "D1",
        size_p(Fraction(1025 - 1), 2) == Fraction(1, 1024),
        "to the 2-observer, 1 and 1025 are 1/1024 apart: their difference is 2 ten times over",
    )
    x = Fraction(1000)
    check(
        "D2",
        (size_p(x, 2), size_p(x, 5), product_over_observers(x)) == (Fraction(1, 8), Fraction(1, 125), 1),
        "product formula for 1000: 1000 * 1/8 * 1/125 = 1",
    )
    rng = Rng("product-formula")
    bad = 0
    for _ in range(2000):
        num = 1 + rng.below(10**6)
        den = 1 + rng.below(10**6)
        sign = -1 if rng.below(2) else 1
        if product_over_observers(Fraction(sign * num, den)) != 1:
            bad += 1
    check("D3", bad == 0, "product formula, exactly, for 2000 random nonzero fractions")

    leaks = 0
    for _ in range(3000):
        p = [2, 3, 5, 7][rng.below(4)]
        a, b, c = (rng.below(10**6) for _ in range(3))
        if len({a, b, c}) < 3:
            continue
        ab, bc, ac = (size_p(Fraction(u - v), p) for u, v in ((a, b), (b, c), (a, c)))
        if ac > max(ab, bc):
            leaks += 1
    plain = (Fraction(2, 5), Fraction(1, 2), Fraction(3, 5))
    ordinary_leaks = abs(plain[0] - plain[2]) > max(abs(plain[0] - plain[1]), abs(plain[1] - plain[2]))
    check(
        "D4",
        leaks == 0 and ordinary_leaks,
        "law 2' on 3000 random triples: prime observers never leak (distance to the far end <= the larger link); ordinary size does (0.4, 0.5, 0.6)",
    )

    bad = 0
    for _ in range(2000):
        depth = 1 + rng.below(6)
        words = [tuple(rng.below(3) for _ in range(depth)) for _ in range(3)]

        def cost(u, v):
            for i, (s, t) in enumerate(zip(u, v)):
                if s != t:
                    return i + 1
            return math.inf

        if cost(words[0], words[2]) < min(cost(words[0], words[1]), cost(words[1], words[2])):
            bad += 1
    check("D5", bad == 0, "law 2' on 2000 random ladders of yes/no observers: the price of telling the ends apart is at least the cheaper link's")


# --------------------------------------------------------------------------
# E. The calculus on random finite models
# --------------------------------------------------------------------------
# A model: a few objects; a few primitive tests, each a value in [0, 1] per
# object and a cost; a few maps from objects to objects, each with a cost.
# The observer may run a map and then a test, paying both costs, so the tests
# of cost <= b are everything reachable that way. d_b(x, y) is the largest gap
# any of them shows.

CAP = 8


def closure(prims, maps, n_obj: int) -> dict[tuple, int]:
    best: dict[tuple, int] = {}
    heap = [(c, v) for v, c in prims]
    heapq.heapify(heap)
    while heap:
        c, v = heapq.heappop(heap)
        if c > CAP or best.get(v, CAP + 1) <= c:
            continue
        best[v] = c
        for fm, fc in maps:
            w = tuple(v[fm[x]] for x in range(n_obj))  # (t after f)(x) = t(f(x))
            if c + fc <= CAP and best.get(w, CAP + 1) > c + fc:
                heapq.heappush(heap, (c + fc, w))
    return best


def distances(best: dict[tuple, int], n_obj: int) -> list[list[list[Fraction]]]:
    """d[b][x][y] for b = 0..CAP."""
    d = [[[Fraction(0)] * n_obj for _ in range(n_obj)] for _ in range(CAP + 1)]
    for v, c in best.items():
        for x in range(n_obj):
            for y in range(n_obj):
                gap = abs(v[x] - v[y])
                for b in range(c, CAP + 1):
                    if gap > d[b][x][y]:
                        d[b][x][y] = gap
    return d


def section_e() -> None:
    rng = Rng("models")
    n_models = 200
    fails = {"law1": 0, "law2": 0, "law3": 0, "price": 0}
    free_substitution_fails = 0  # negative control for law 3
    ultrametric_fails = 0  # negative control for law 2
    limit_ok = 0
    for _ in range(n_models):
        n_obj = 4 + rng.below(3)
        prims = []
        for _ in range(3):
            prims.append((tuple(Fraction(rng.below(5), 4) for _ in range(n_obj)), 1 + rng.below(3)))
        for x in range(n_obj):  # dear tests that separate every point: the classical limit
            prims.append((tuple(Fraction(int(i == x)) for i in range(n_obj)), CAP))
        maps = [(tuple(rng.below(n_obj) for _ in range(n_obj)), 1 + rng.below(2)) for _ in range(2)]
        d = distances(closure(prims, maps, n_obj), n_obj)
        R = range(n_obj)

        if any(d[b + 1][x][y] < d[b][x][y] for b in range(CAP) for x in R for y in R):
            fails["law1"] += 1
        if any(d[b][x][z] > d[b][x][y] + d[b][y][z] for b in range(CAP + 1) for x in R for y in R for z in R):
            fails["law2"] += 1
        if any(d[b][x][z] > max(d[b][x][y], d[b][y][z]) for b in range(CAP + 1) for x in R for y in R for z in R):
            ultrametric_fails += 1
        if any(
            d[b][fm[x]][fm[y]] > d[b + fc][x][y]
            for fm, fc in maps
            for b in range(CAP + 1 - fc)
            for x in R
            for y in R
        ):
            fails["law3"] += 1
        if any(d[b][fm[x]][fm[y]] > d[b][x][y] for fm, fc in maps for b in range(CAP + 1) for x in R for y in R):
            free_substitution_fails += 1

        def price_eps(x, y, eps):
            for b in range(CAP + 1):
                if d[b][x][y] > eps:
                    return b
            return math.inf

        grid = [Fraction(0), Fraction(1, 4), Fraction(1, 2)]
        if any(
            price_eps(x, z, e1 + e2) < min(price_eps(x, y, e1), price_eps(y, z, e2))
            for e1 in grid
            for e2 in grid
            for x in R
            for y in R
            for z in R
        ):
            fails["price"] += 1
        if all((d[CAP][x][y] == 0) == (x == y) for x in R for y in R):
            limit_ok += 1

    check("E1", fails["law1"] == 0, f"law 1 (more budget, never less difference) in {n_models} random models")
    check(
        "E2",
        fails["law2"] == 0 and ultrametric_fails > 0,
        f"law 2 (errors add along a chain) in {n_models} models; the leak-free version fails in {ultrametric_fails} of them",
    )
    check(
        "E3",
        fails["law3"] == 0 and free_substitution_fails > 0,
        f"law 3 (substitution costs) in {n_models} models; free substitution fails in {free_substitution_fails} of them",
    )
    check("E4", fails["price"] == 0, f"price form of laws 2 and 2' in {n_models} models: price at eps+delta >= the cheaper link's price")
    check("E5", limit_ok == n_models, f"classical limit in {n_models} models: at full budget, distance 0 exactly when the objects are the same")


# --------------------------------------------------------------------------
# F. A real, weak observer counts the same information twice
# --------------------------------------------------------------------------
# zlib stands in for an observer with a small budget: it finds repeats but
# cannot afford to notice that one string is another one backwards.


def packed(data: bytes, given: bytes = b"") -> int:
    c = zlib.compressobj(9, zlib.DEFLATED, 15, 9, zlib.Z_DEFAULT_STRATEGY, given) if given else zlib.compressobj(9)
    return len(c.compress(data) + c.flush())


def section_f() -> None:
    n = 4000
    x = Rng("zlib-demo").bytes(n)
    y = x[::-1]  # an easy map: the same bytes backwards
    alone = packed(x)
    y_given_x = packed(y, x)  # what y still costs an observer who already holds x
    y_undone_given_x = packed(y[::-1], x)  # the same observer after spending the cost of the map
    say(f"  bytes: x alone {alone}, y given x {y_given_x}, y turned round given x {y_undone_given_x}")
    check(
        "F1",
        alone > 0.9 * n and y_given_x > 0.9 * n and y_undone_given_x < 0.05 * n,
        f"x and its reversal hold one string's worth of information; zlib charges for two ({alone} + {y_given_x} bytes) until the reversal is undone ({y_undone_given_x})",
    )


def main() -> int:
    for title, fn in (
        ("A. Coins: sameness as a curve", section_a),
        ("B. Parity: computing can create distinctions", section_b),
        ("C. Several observers at once", section_c),
        ("D. Primes as observers", section_d),
        ("E. The calculus on random finite models", section_e),
        ("F. A weak observer counts twice", section_f),
    ):
        print(title)
        fn()
    failed = [name for ok, name, _ in RESULTS if not ok]
    print(f"{len(RESULTS)} checks, {len(failed)} failed" + (": " + ", ".join(failed) if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
