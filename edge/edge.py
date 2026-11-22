#!/usr/bin/env python3
"""edge.py - every computed number in "The edge the zeros sit on", reproduced.

The notes this file ships with follow one sentence: order on one side, non-order on the
other, and something exact sitting between them. The Riemann zeta function is the main
example, and five smaller ones stand beside it. This program does not prove the notes.
It does two smaller things:

  1. recomputes every number the notes mark [computed], and
  2. puts a control beside each claim where one is possible, the same test failing on
     a perturbed object, so that a check cannot pass by being empty.

Usage:
    python3 edge/edge.py            # run everything
    python3 edge/edge.py C E        # run only sections C and E
    python3 edge/edge.py -v         # also print the tables some sections keep

Standard library only. No network, no files written. Exit status 0 if every check
passes, 1 if one fails, 2 if the arguments are not understood. Randomness comes only
from random.Random(seed).random(), the one sequence Python promises to keep, so the
simulated numbers are the same everywhere; floating-point results can differ in the
last digits between machines and Python versions, and the tolerances allow for that.

Literal numbers in the pass conditions are of two kinds, and comments say which:
values from outside (a table, a theorem), and regression values produced by an
earlier run of this program, which only guard against the code changing.
"""
from __future__ import annotations

import cmath
import math
import operator
import random
import sys
from fractions import Fraction
from operator import mul

PI = math.pi
VERBOSE = "-v" in sys.argv[1:]
RESULTS: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str) -> None:
    """Record one check and print it. `detail` carries the numbers that were computed. It is
    written as the statement that should hold, so a failing line is flagged as not confirmed."""
    RESULTS.append((bool(ok), name, detail))
    print(("ok   " if ok else "FAIL ") + name + "  " + ("" if ok else "NOT CONFIRMED, this did not hold as written: ") + detail)


def tiny(v: float) -> str:
    """A small error, for printing. Values at rounding level are shown as a bound, not as a figure."""
    return f"{v:.0e}" if v >= 1e-15 else "under 1e-15"


def say(text: str = "") -> None:
    if VERBOSE:
        print(text)


class Rng:
    """Portable randomness. Only random.Random(seed).random() is used, the one sequence
    Python promises not to change between versions; everything else is derived from it."""

    def __init__(self, seed: int) -> None:
        self._r = random.Random(seed)
        self._spare: float | None = None

    def uniform(self) -> float:
        return self._r.random()

    def below(self, k: int) -> int:
        return min(k - 1, int(self._r.random() * k))

    def gauss(self) -> float:
        if self._spare is not None:
            z, self._spare = self._spare, None
            return z
        u1 = 1.0 - self._r.random()  # in (0, 1]
        u2 = self._r.random()
        r = math.sqrt(-2.0 * math.log(u1))
        self._spare = r * math.sin(2 * PI * u2)
        return r * math.cos(2 * PI * u2)


# ---------------------------------------------------------------- special functions

_STIRLING = [1 / 12, -1 / 360, 1 / 1260, -1 / 1680, 1 / 1188, -691 / 360360, 1 / 156]


def loggamma(z: complex) -> complex:
    """log Gamma(z). For Re z > 0 this is the branch that is real on the positive axis;
    for Re z <= 0 it may be off by a multiple of 2 pi i, which exp() does not see."""
    z = complex(z)
    if z.real <= 0:
        return cmath.log(PI / cmath.sin(PI * z)) - loggamma(1 - z)
    shift = 0j
    while z.real < 15:
        shift += cmath.log(z)
        z += 1
    zi = 1 / z
    zi2 = zi * zi
    series, term = 0j, zi
    for c in _STIRLING:
        series += c * term
        term *= zi2
    return (z - 0.5) * cmath.log(z) - z + 0.5 * math.log(2 * PI) + series - shift


def cgamma(z: complex) -> complex:
    return cmath.exp(loggamma(z))


_B2K = [1 / 6, -1 / 30, 1 / 42, -1 / 30, 5 / 66, -691 / 2730, 7 / 6]  # B2 .. B14
_FACT2K = [2, 24, 720, 40320, 3628800, 479001600, 87178291200]  # (2k)!


def hurwitz(s: complex, a: float = 1.0, n_terms: int | None = None) -> complex:
    """Hurwitz zeta, the sum over n >= 0 of (n + a)^(-s), continued to all s != 1 by
    Euler-Maclaurin summation. Costs about |s| + 25 terms; good to ~1e-12 for |s| < 1e4."""
    s = complex(s)
    big_n = n_terms if n_terms is not None else max(30, int(abs(s)) + 25)
    total = 0j
    for n in range(big_n):
        total += cmath.exp(-s * math.log(n + a))
    x = big_n + a
    lx = math.log(x)
    total += cmath.exp((1 - s) * lx) / (s - 1) + 0.5 * cmath.exp(-s * lx)
    term = s * cmath.exp((-s - 1) * lx)
    for k in range(len(_B2K)):
        total += _B2K[k] / _FACT2K[k] * term
        term *= (s + 2 * k + 1) * (s + 2 * k + 2) / (x * x)
    return total


def zeta(s: complex) -> complex:
    return hurwitz(s, 1.0)


def xi(s: complex) -> complex:
    """The completed zeta function: xi(s) = xi(1 - s), entire, same zeros as zeta in the strip."""
    s = complex(s)
    return 0.5 * s * (s - 1) * cmath.exp(-(s / 2) * math.log(PI) + loggamma(s / 2)) * zeta(s)


def chi(s: complex) -> complex:
    """The factor in the functional equation zeta(s) = chi(s) zeta(1 - s)."""
    s = complex(s)
    return cmath.exp(s * math.log(2) + (s - 1) * math.log(PI) + loggamma(1 - s)) * cmath.sin(PI * s / 2)


def theta(t: float) -> float:
    """Riemann-Siegel theta: Z(t) = exp(i theta(t)) zeta(1/2 + it) is real for real t."""
    return loggamma(0.25 + 0.5j * t).imag - 0.5 * t * math.log(PI)


# ---------------------------------------------------------------- the density behind xi


def g_bump(v: float) -> float:
    """One integer's bump, before its shift and weight."""
    return (2 * PI ** 2 * math.exp(4.5 * v) - 3 * PI * math.exp(2.5 * v)) * math.exp(-PI * math.exp(2 * v))


def phi_series(u: float, n_max: int = 400) -> float:
    """Phi(u) summed as written: 2 * sum over n of n^(-1/2) g_bump(u + log n). For u < 0 the
    terms are large and cancel, so this loses digits there; use phi() for values."""
    return 2 * sum(n ** -0.5 * g_bump(u + math.log(n)) for n in range(1, n_max + 1))


def phi(u: float) -> float:
    """Phi(u), the even positive density whose Fourier transform is xi(1/2 + ix)."""
    return phi_series(abs(u), 8)


def xi_from_phi(x: float, h: float = 0.005, u_max: float = 1.5) -> float:
    """integral of Phi(u) e^(ixu) du by the trapezoid rule (double precision: fine for x < 30)."""
    k = int(round(u_max / h))
    return 2 * h * (0.5 * phi(0.0) + sum(phi(j * h) * math.cos(x * j * h) for j in range(1, k + 1)))


# ---------------------------------------------------------------- root finding and counting


def bisect(f, a: float, b: float, tol: float = 1e-12, max_iter: int = 200) -> float:
    """A root of f in [a, b], given a sign change."""
    fa, fb = f(a), f(b)
    if fa == 0:
        return a
    if fb == 0:
        return b
    if (fa > 0) == (fb > 0):
        raise ValueError("bisect: no sign change")
    for _ in range(max_iter):
        m = 0.5 * (a + b)
        fm = f(m)
        if fm == 0 or (b - a) < tol:
            return m
        if (fm > 0) == (fa > 0):
            a, fa = m, fm
        else:
            b, fb = m, fm
    return 0.5 * (a + b)


def winding(f, vertices: list[complex], pieces: int = 8, tol: float = 0.6, max_depth: int = 30) -> int:
    """How many zeros an analytic f has inside the closed polygon `vertices` (counter-clockwise):
    the total change of arg f along the boundary over 2 pi. Each edge is first cut into `pieces`,
    then halved until the argument moves by less than `tol` per step."""

    def seg(a: complex, fa: complex, b: complex, fb: complex, depth: int) -> float:
        d = cmath.phase(fb / fa)
        if abs(d) < tol or depth >= max_depth:
            return d
        m = 0.5 * (a + b)
        fm = f(m)
        return seg(a, fa, m, fm, depth + 1) + seg(m, fm, b, fb, depth + 1)

    total = 0.0
    n = len(vertices)
    for i in range(n):
        a, b = vertices[i], vertices[(i + 1) % n]
        pts = [a + (b - a) * j / pieces for j in range(pieces + 1)]
        vals = [f(p) for p in pts]
        for j in range(pieces):
            total += seg(pts[j], vals[j], pts[j + 1], vals[j + 1], 0)
    return round(total / (2 * PI))


def poly_eval(coeffs: list[complex], x: complex) -> complex:
    """c[0] + c[1] x + ... + c[n] x^n."""
    acc = 0j
    for c in reversed(coeffs):
        acc = acc * x + c
    return acc


def poly_residual(coeffs: list[complex], roots: list[complex]) -> float:
    """Largest |p(r)| over the given values r, relative to the size of p's terms there
    (infinite if a value is not a number). Durand-Kerner returns whatever it has when it stops,
    so this is the caller's test of what came back. A small value means each r is a root of a
    nearby polynomial; near a multiple root that is weaker than being near the root."""
    worst = 0.0
    for r in roots:
        scale = sum(abs(c) * abs(r) ** k for k, c in enumerate(coeffs))
        res = abs(poly_eval(coeffs, r)) / scale if scale > 0 else math.inf
        if not res <= worst:  # also true when res is not a number
            worst = res if res == res else math.inf
    return worst


def poly_roots(coeffs: list[complex], max_iter: int = 2000, tol: float = 1e-13) -> list[complex]:
    """All roots of c[0] + c[1] x + ... + c[n] x^n by the Durand-Kerner iteration.
    Reliable for simple roots up to degree ~40; multiple roots converge slowly."""
    c = [complex(x) for x in coeffs]
    while len(c) > 1 and c[-1] == 0:
        c.pop()
    n = len(c) - 1
    if n < 1:
        return []
    c = [x / c[-1] for x in c]
    radius = max((abs(c[k]) ** (1.0 / (n - k)) for k in range(n) if c[k] != 0), default=1.0)
    roots = [radius * (0.4 + 0.9j) ** k for k in range(n)]
    for _ in range(max_iter):
        worst = 0.0
        for i in range(n):
            num = poly_eval(c, roots[i])
            den = 1 + 0j
            for j in range(n):
                if j != i:
                    den *= roots[i] - roots[j]
            if den == 0:
                den = 1e-30
            step = num / den
            roots[i] -= step
            worst = max(worst, abs(step))
        if worst < tol:
            break
    return roots


# ====================================================================================================
# section A: density

TITLE_DENSITY = "A. The density behind zeta: one lopsided bump for every integer"


def density_kuiper_pdf(y: float, k_max: int = 60) -> float:
    """Density of Y = sqrt(2/pi) V, where V has Kuiper's limit law
    P(V <= x) = 1 - 2 sum_k (4 k^2 x^2 - 1) exp(-2 k^2 x^2); the same law as the height of a
    Brownian excursion and the range of a Brownian bridge."""
    return 4 * sum((2 * PI ** 2 * k ** 4 * y ** 3 - 3 * PI * k * k * y) * math.exp(-PI * k * k * y * y) for k in range(1, k_max + 1))


def density_moment(s: complex, h: float = 0.001) -> complex:
    """E[Y^s], integrating the Kuiper density itself: the trapezoid rule on 0.25 <= y <= 5.
    Outside that range the density is below 1e-13 (it is 2 Phi(u) e^(-3u/2) at y = e^u, and
    Phi(1.3) is 6e-15), and the series for it is accurate to rounding inside."""
    total = 0j
    n0, n1 = int(round(0.25 / h)), int(round(5.0 / h))
    for j in range(n0, n1 + 1):
        y = j * h
        weight = 0.5 if j in (n0, n1) else 1.0
        total += weight * density_kuiper_pdf(y, 30) * cmath.exp(s * math.log(y))
    return total * h


def density_kuiper_sample(rng: Rng, n: int) -> float:
    """Kuiper's statistic for n uniform points, scaled to its limit law (Stephens' correction)."""
    xs = sorted(rng.uniform() for _ in range(n))
    d_plus = max((i + 1) / n - x for i, x in enumerate(xs))
    d_minus = max(x - i / n for i, x in enumerate(xs))
    root = math.sqrt(n)
    return (root + 0.155 + 0.24 / root) * (d_plus + d_minus)


def section_density() -> None:
    grid = [i * 0.05 for i in range(25)]
    uneven = max(abs(phi_series(u) - phi_series(-u)) for u in grid)
    lowest = min(phi(i * 0.01) for i in range(131))
    scan = [(g_bump(-2 + 0.001 * i), -2 + 0.001 * i) for i in range(3001)]
    trough, trough_at = min(scan)
    peak, peak_at = max(scan)
    check(
        "A1",
        uneven < 1e-12 and lowest > 0 and abs(g_bump(0.3) - g_bump(-0.3)) > 0.05 and trough < -0.3,
        f"Phi is even (largest |Phi(u) - Phi(-u)| on [0, 1.2] is {uneven:.0e}, from the series as written, which is not even term by term) "
        f"and positive (least value on [0, 1.3] is {lowest:.1e}); a single term g is neither: g(0.3) = {g_bump(0.3):.4f} but g(-0.3) = {g_bump(-0.3):.4f}, "
        f"and beside its peak of {peak:.3f} at v = {peak_at:.2f} it has a trough of {trough:.3f} at v = {trough_at:.2f}",
    )

    worst = 0.0
    for x in (0.0, 5.0, 10.0, 20.0, 26.0):
        want = xi(0.5 + 1j * x).real
        worst = max(worst, abs(xi_from_phi(x) - want) / abs(want))
    zeros = []
    step = 0.25
    x = 10.0
    while x < 27.0:
        if (xi_from_phi(x) > 0) != (xi_from_phi(x + step) > 0):
            zeros.append(bisect(xi_from_phi, x, x + step, 1e-9))
        x += step
    at_zeta = max(abs(zeta(0.5 + 1j * z)) for z in zeros) if zeros else 1.0
    check(
        "A2",
        worst < 1e-7 and len(zeros) == 3 and at_zeta < 1e-6,
        f"the Fourier transform of Phi is xi on the critical line (relative gap at five heights at most {worst:.0e}, with xi from gamma and zeta); "
        f"its sign changes below 27 are at {', '.join(f'{z:.4f}' for z in zeros)}, where |zeta(1/2 + it)| is at most {at_zeta:.0e}",
    )

    def lopsided(n_max: int) -> float:
        return abs(phi_series(1.0, n_max) - phi_series(-1.0, n_max))

    parts = [(n, lopsided(n)) for n in (1, 2, 4, 8, 50)]
    check(
        "A3",
        parts[0][1] > 0.1 and parts[-1][1] < 1e-12 and all(a[1] > b[1] for a, b in zip(parts, parts[1:])),
        "Phi(u) = 2 sum n^(-1/2) g(u + log n): no partial sum is even, the whole sum is. |sum(1) - sum(-1)| with the integers up to "
        + ", ".join(f"{n}: {v:.1e}" for n, v in parts),
    )

    ident = max(abs(density_kuiper_pdf(math.exp(u)) * math.exp(1.5 * u) - 2 * phi(u)) for u in [-0.5 + 0.05 * i for i in range(37)])
    off = abs(density_kuiper_pdf(math.exp(0.2)) * math.exp(1.4 * 0.2) - 2 * phi(0.2))  # control: the wrong tilt
    mass = density_moment(0j).real
    mean_v = density_moment(1 + 0j).real * math.sqrt(PI / 2)  # the mean of Kuiper's variable itself: sqrt(pi/2), a known value
    gaps = []
    for s in (2 + 0j, 3 + 2j, 0.5 + 10j, 0.25 + 3j):
        want = 2 * xi(s)
        gaps.append(abs(density_moment(s) - want) / abs(want))
    check(
        "A4",
        ident < 1e-12 and off > 1e-3 and max(gaps) < 1e-9 and abs(mass - 1) < 1e-10 and abs(mean_v - math.sqrt(PI / 2)) < 1e-10,
        f"let V have Kuiper's limit law (the range of a Brownian bridge, the height of a Brownian excursion) and Y = sqrt(2/pi) V. Integrating Kuiper's density itself: "
        f"total mass {mass:.12f}, mean of V {mean_v:.10f} against sqrt(pi/2) = {math.sqrt(PI / 2):.10f}, and E[Y^s] = 2 xi(s) at s = 2, 3 + 2i, 1/2 + 10i, 1/4 + 3i "
        f"(relative gap at most {max(gaps):.0e}; by arithmetic, the constant sqrt(pi/2) in place of sqrt(2/pi) would put the second moment out by a factor of {(PI / 2) ** 2:.2f}). "
        f"Point by point, the density of log Y tilted by sqrt(Y) is 2 Phi (largest gap for -0.5 <= log Y <= 1.3: {ident:.0e}; with the wrong tilt {off:.1e})",
    )

    rng = Rng(20261122)
    points, runs = 800, 2500
    ys = [math.sqrt(2 / PI) * density_kuiper_sample(rng, points) for _ in range(runs)]
    rows = []
    ok = True
    errs = []
    for x in (0.0, 10.0, zeros[0] if zeros else 14.134725):
        vals = [math.sqrt(y) * math.cos(x * math.log(y)) for y in ys]
        got = sum(vals) / len(vals)
        err = math.sqrt(sum((v - got) ** 2 for v in vals) / (len(vals) - 1) / len(vals))
        want = 2 * xi_from_phi(x)
        errs.append(err)
        rows.append(f"x = {x:.4f}: {got:+.4f} against " + ("0" if abs(want) < 5e-5 else f"{want:+.4f}") + f" (sampling error {err:.4f})")
        ok = ok and abs(got - want) < 3 * err
    # what a sample of this size can and cannot see near the first zero
    drowned_from = bisect(lambda x: 2 * xi_from_phi(x) - errs[-1], 10.0, 14.0, 1e-6)
    deepest = min(2 * xi_from_phi(14.2 + 0.1 * j) for j in range(110))
    check(
        "A5",
        ok and deepest > -errs[-1] / 3,
        f"simulated: Kuiper's statistic on {points} uniform points, {runs} times; the mean of sqrt(Y) cos(x log Y) against twice the transform of Phi, "
        "each within three sampling errors. " + "; ".join(rows) + ". The sample is consistent with a zero at the last height and cannot locate it: the exact transform "
        f"is within one sampling error of 0 at every height from {math.ceil(drowned_from * 10) / 10:.1f} up to 25, the range scanned, and beyond the zero it never falls below {deepest:.4f} there",
    )


# ====================================================================================================
# section B: coins

TITLE_COINS = "B. Two coins and small magnets: attraction keeps zeros on the line"


def coins_partition_poly(n: int, coupling) -> list[float]:
    """Coefficients in z of sum over spin configurations of exp(sum_{i<j} J_ij s_i s_j) z^(number of down spins).
    With z = e^(-2h) this is the partition function in a magnetic field h, up to a factor."""
    coeffs = [0.0] * (n + 1)
    for mask in range(1 << n):
        spins = [-1 if mask >> i & 1 else 1 for i in range(n)]
        energy = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                energy += coupling(i, j) * spins[i] * spins[j]
        coeffs[bin(mask).count("1")] += math.exp(energy)
    return coeffs


def coins_off_circle(coeffs: list[float]) -> tuple[float, float]:
    """(how far the furthest zero is from the unit circle, the residual showing the values found are zeros)"""
    roots = poly_roots(coeffs)
    return max(abs(abs(z) - 1) for z in roots), poly_residual(coeffs, roots)


def coins_weighted(coeffs: list[float], eps: float) -> list[float]:
    """Weight the magnetisation M by e^(-eps M^2). Coefficient k belongs to k spins down, M = n - 2k."""
    n = len(coeffs) - 1
    return [c * math.exp(-eps * (n - 2 * k) ** 2) for k, c in enumerate(coeffs)]


def coins_not_proportional(a: list[float], b: list[float]) -> float:
    """0 when the two coefficient lists are the same polynomial up to a constant factor."""
    ratios = [x / y for x, y in zip(a, b)]
    return max(ratios) / min(ratios) - 1


def section_coins() -> None:
    # heads minus tails of two coins, agreement weighted by e^(4 eps): transform 2 + 2 e^(4 eps) cos 2y
    rows = []
    ok = True
    for eps in (0.05, 0.0, -0.05):
        c = -math.exp(-4 * eps)
        if abs(c) <= 1:
            t1 = 0.5 * math.acos(c)
            zs = [complex(t1), complex(PI - t1)]
            rows.append(f"eps = {eps:+.2f}: real zeros at {t1:.4f} and {PI - t1:.4f}")
            ok = ok and (eps == 0) == (abs(zs[0] - zs[1]) < 1e-6)  # float == is exact here: eps is literally 0.0
        else:
            b = 0.5 * math.acosh(-c)
            zs = [complex(PI / 2, b), complex(PI / 2, -b)]
            rows.append(f"eps = {eps:+.2f}: no real zero, a mirror pair at pi/2 +- {b:.4f}i")
            ok = ok and eps < 0
        ok = ok and all(abs(2 + 2 * math.exp(4 * eps) * cmath.cos(2 * z)) < 1e-9 for z in zs)
    check("B1", ok, "two coins, heads minus tails, agreement weighted by e^(4 eps); zeros of the transform 2 + 2 e^(4 eps) cos 2y. " + "; ".join(rows))

    rng = Rng(1952)
    worst_ferro, best_anti, worst_residual = 0.0, float("inf"), 0.0
    for _ in range(5):
        table = {}
        for i in range(8):
            for j in range(i + 1, 8):
                table[(i, j)] = 0.5 * rng.uniform()
        off, res = coins_off_circle(coins_partition_poly(8, lambda i, j: table[(i, j)]))
        worst_ferro, worst_residual = max(worst_ferro, off), max(worst_residual, res)
        off, res = coins_off_circle(coins_partition_poly(8, lambda i, j: -0.3 * table[(i, j)]))
        best_anti, worst_residual = min(best_anti, off), max(worst_residual, res)
    check(
        "B2",
        worst_ferro < 1e-8 and best_anti > 0.05 and worst_residual < 1e-9,
        f"Lee and Yang's theorem on five random magnets of 8 spins: with every coupling attractive, every zero in z = e^(-2h) is on the unit circle "
        f"(furthest from it: {tiny(worst_ferro)}), which means a purely imaginary field; with the couplings made repulsive at three tenths the strength, "
        f"zeros leave the circle (in each magnet some zero is at least {best_anti:.2f} from it). All eighty values found are zeros (residual {tiny(worst_residual)})",
    )

    # e^(-eps M^2) on the magnetisation is the same as taking 2 eps of attraction from every pair,
    # because M^2 = n + 2 * (sum of the pairwise products)
    j0, n = 0.2, 8
    base = coins_partition_poly(n, lambda i, j: j0)
    same = max(coins_not_proportional(coins_weighted(base, e), coins_partition_poly(n, lambda i, j: j0 - 2 * e)) for e in (0.09, 0.11))
    not_same = coins_not_proportional(coins_weighted(base, 0.09), coins_partition_poly(n, lambda i, j: j0 - 0.09))  # control: one eps per pair, not two
    inside, res1 = coins_off_circle(coins_weighted(base, 0.09))
    outside, res2 = coins_off_circle(coins_weighted(base, 0.11))
    # the theorem is a guarantee, not a limit: weaken one pair to 0.05, so that the guarantee ends at eps = 0.025
    weak = coins_partition_poly(n, lambda i, j: 0.05 if (i, j) == (0, 1) else j0)
    still, res3 = coins_off_circle(coins_weighted(weak, 0.08))
    gone, res4 = coins_off_circle(coins_weighted(weak, 0.09))
    spread = coins_partition_poly(6, lambda i, j: 0.0)
    binomial = [math.comb(6, k) for k in range(7)]
    check(
        "B3",
        same < 1e-10 and not_same > 0.01 and inside < 1e-8 and outside > 0.01 and still < 1e-8 and gone > 0.01 and max(res1, res2, res3, res4) < 1e-9
        and max(abs(a - b) for a, b in zip(spread, binomial)) < 1e-12,
        f"weighting a magnet's magnetisation M by e^(-eps M^2) takes 2 eps of attraction from every pair: for eight spins with every pair attracting by 0.2, "
        f"the weighted polynomial is the polynomial of the magnet with couplings 0.2 - 2 eps, up to a constant factor (to {tiny(same)} at eps = 0.09 and 0.11; "
        f"control, with 0.2 - eps instead, the ratio of coefficients varies by a factor of {1 + not_same:.1f}). Its zeros are on the circle at eps = 0.09 ({tiny(inside)}) and off it at eps = 0.11 ({outside:.3f}): "
        f"with equal couplings the zeros leave exactly when the attraction runs out. That is not so in general, because the theorem is a guarantee and not a limit: "
        f"with one pair weakened to 0.05 the guarantee ends at eps = 0.025, yet the zeros are still on the circle at eps = 0.08 ({tiny(still)}), where that pair repels by 0.11, "
        f"and leave only by eps = 0.09 ({gone:.3f}). Six spins with no coupling give (1 + z)^6, all six zeros at one point: independence is the edge itself",
    )


# ====================================================================================================
# section C: flow

TITLE_FLOW = "C. De Bruijn and Newman's flow: forward the zeros spread out, backward they meet and leave the axis"

# the heights of zeta's first twenty zeros, as the notes list them
flow_LISTED = [14.1347, 21.0220, 25.0109, 30.4249, 32.9351, 37.5862, 40.9187, 43.3271, 48.0052, 49.7738,
               52.9703, 56.4462, 59.3470, 60.8318, 65.1125, 67.0798, 69.5464, 72.0672, 75.7047, 77.1448]
flow_TOP = 78.3  # a height between the 20th zero (77.14) and the 21st (79.34)
flow_HIGH = 113.0  # a height between the 35th zero (111.87) and the 36th (114.32)
flow_FAR = 417.0  # a height between the 213th zero (415.46) and the 214th (418.39)
flow_NAMES = ("C1a", "C1b", "C1c", "C1d", "C2a", "C2b", "C3a", "C3b", "C4a", "C4b", "C5", "C6a", "C6b", "C7a", "C7b", "C7c")


class flow_Engine:
    """H(tau, x) = integral of e^(tau u^2) Phi(u) e^(ixu) du, and its x-derivatives, in integer arithmetic.

    |H| falls like e^(-pi x / 4) while Phi is of size 1, so near x = 78 the integral is a sum of terms of
    size 1 that cancels to 1e-23: ordinary floating point is useless there. Here an integer n stands for
    the number n / 2^bits, which makes every addition exact and every product good to 2^-bits.
    The integral is the trapezoid sum over u = j / per_unit, |u| <= u_max. Phi is even and falls like
    exp(-pi e^(2u)), so the cut at u_max costs nothing; the rule's own error is H at the aliased points
    x +- 2 pi per_unit, which is far smaller than H(x) while 2 pi per_unit is well above 2x. The cosines
    are summed by Clenshaw's recurrence, one big multiplication per sample point. C1a measures all of
    this by running a finer copy."""

    def __init__(self, bits: int, per_unit: int, u_max: float) -> None:
        self.bits, self.m, self.n = bits, per_unit, int(u_max * per_unit)
        self.one = 1 << bits
        self.pi = 16 * self._atan_inv(5) - 4 * self._atan_inv(239)  # Machin
        self.phi = [self._phi(j) for j in range(self.n + 1)]
        self._weights: dict = {}
        self._trig: dict = {}

    def fix(self, x) -> int:
        """A float, int or Fraction as a scaled integer; floats are binary fractions, so this is exact."""
        num, den = x.as_integer_ratio()
        return (num << self.bits) // den

    def _atan_inv(self, k: int) -> int:
        term = self.one // k
        total, j, sign = term, 1, -1
        while term:
            term //= k * k
            j += 2
            total += sign * (term // j)
            sign = -sign
        return total

    def exp(self, y: int) -> int:
        """e^y: halve y until it is below 1/256, sum the Taylor series, square back."""
        p = self.bits
        halvings = max(0, y.bit_length() - (p - 8))
        r = y >> halvings
        total = term = self.one
        j = 1
        while term:
            term = ((term * r) >> p) // j
            total += term
            j += 1
        for _ in range(halvings):
            total = (total * total) >> p
        return total

    def cos_sin(self, theta: int, with_sin: bool = True) -> tuple[int, int]:
        """cos and sin: the Taylor series at theta / 2^k, then k angle doublings. Without with_sin, sin is left 0."""
        p = self.bits
        halvings = max(0, theta.bit_length() - (p - 6))
        t = theta >> halvings
        t2 = (t * t) >> p
        c = term = self.one
        j = 0
        while term:
            j += 2
            term = -((term * t2) >> p) // (j * (j - 1))
            c += term
        s = 0
        if with_sin:
            s = term = t
            j = 1
            while term:
                j += 2
                term = -((term * t2) >> p) // (j * (j - 1))
                s += term
        for _ in range(halvings):
            c, s = ((c * c) >> (p - 1)) - self.one, (s * c) >> (p - 1)
        return c, s

    def trig(self, x: float, with_sin: bool, keep: bool) -> tuple[int, int]:
        """cos and sin of x / per_unit. Grid points come back for every tau, so theirs are kept."""
        found = self._trig.get(x)
        if found is None:
            found = self.cos_sin(self.fix(x) // self.m, with_sin or keep)
            if keep:
                self._trig[x] = found
        return found

    def _phi(self, j: int) -> int:
        """Phi(j / per_unit) = 2 sum over n of (2 pi^2 n^4 e^(4.5u) - 3 pi n^2 e^(2.5u)) exp(-pi n^2 e^(2u))."""
        p, pi = self.bits, self.pi
        two_u = self.fix(Fraction(2 * j, self.m))
        e2 = self.exp(two_u)
        e25 = (e2 * self.exp(two_u >> 2)) >> p
        e45 = (e2 * e25) >> p
        total, n = 0, 1
        while True:
            q = self.exp(-n * n * ((pi * e2) >> p))
            if q == 0:
                return 2 * total
            total += (((2 * ((pi * pi) >> p) * n ** 4 * e45 - 3 * pi * n * n * e25) >> p) * q) >> p
            n += 1

    def weights(self, tau: float) -> list:
        """For d = 0..3: the samples (j / per_unit)^d e^(tau u^2) Phi(u) times the trapezoid weight, as
        (the one at u = 0, the others from the far end down to j = 1). Kept: each tau is used many times."""
        rows = self._weights.get(tau)
        if rows is None:
            t, m, p = self.fix(tau), self.m, self.bits
            row = [((self.phi[j] * self.exp(t * j * j // (m * m))) >> p) * (2 if j else 1) // m for j in range(self.n + 1)]
            rows = []
            for _ in range(4):
                rows.append((row[0], row[:0:-1]))
                row = [a * j // m for j, a in enumerate(row)]
            self._weights[tau] = rows
        return rows

    def fx(self, tau: float, x: float, d: int = 0, keep: bool = False) -> int:
        """The d-th x-derivative of H(tau, x) at real x, as a scaled integer (so its sign is exact)."""
        first, rest = self.weights(tau)[d]
        p = self.bits
        c, s = self.trig(x, d & 1 == 1, keep)
        c2 = 2 * c
        b1 = b2 = 0
        for a in rest:
            b1, b2 = a + ((c2 * b1) >> p) - b2, b1
        v = (s * b1) >> p if d & 1 else first + ((c * b1) >> p) - b2
        return -v if d in (1, 2) else v  # d/dx takes cos to -u sin, -u^2 cos, u^3 sin

    def val(self, tau: float, x: float, d: int = 0) -> float:
        return self.fx(tau, x, d) / self.one

    def cval(self, tau: float, z: complex, d: int = 0) -> complex:
        """The same at complex x."""
        first, rest = self.weights(tau)[d]
        p, m = self.bits, self.m
        z = complex(z)
        ca, sa = self.cos_sin(self.fix(z.real) // m)
        up, down = self.exp(self.fix(z.imag) // m), self.exp(self.fix(-z.imag) // m)
        ch, sh = (up + down) >> 1, (up - down) >> 1
        cr, ci = (ca * ch) >> p, -((sa * sh) >> p)  # cos(z / m)
        sr, si = (sa * ch) >> p, (ca * sh) >> p  # sin(z / m)
        c2r, c2i = 2 * cr, 2 * ci
        b1r = b1i = b2r = b2i = 0
        for a in rest:
            b1r, b1i, b2r, b2i = a + ((c2r * b1r - c2i * b1i) >> p) - b2r, ((c2r * b1i + c2i * b1r) >> p) - b2i, b1r, b1i
        if d & 1:
            vr, vi = (sr * b1r - si * b1i) >> p, (sr * b1i + si * b1r) >> p
        else:
            vr, vi = first + ((cr * b1r - ci * b1i) >> p) - b2r, ((cr * b1i + ci * b1r) >> p) - b2i
        sign = -1 if d in (1, 2) else 1
        return complex(sign * vr / self.one, sign * vi / self.one)


def flow_bisect(eng: flow_Engine, tau: float, a: float, b: float, d: int = 0, tol: float = 2e-12) -> float:
    """A zero of the d-th derivative between a and b, by bisection on exact signs."""
    if b - a > tol:
        side = eng.fx(tau, a, d) > 0
        while b - a > tol:
            mid = 0.5 * (a + b)
            if (eng.fx(tau, mid, d) > 0) == side:
                a = mid
            else:
                b = mid
    return 0.5 * (a + b)


def flow_real_zeros(eng: flow_Engine, tau: float, lo: float, hi: float, cell: float = 0.1, tol: float = 2e-12) -> list[float]:
    """Every real zero of H(tau, .) in [lo, hi]. A sign change between grid points is one zero. Two zeros
    hiding in one cell need a turning point between them, so wherever dH/dx changes sign and H does not,
    the turning point is found and H is looked at there. The turning point is located to 1e-6, which
    catches any pair more than about 1e-6 apart (to 0.001 when tol is coarse and the call only counts)."""
    if not math.isfinite(tau + lo + hi):
        return []
    n = int(math.ceil((hi - lo) / cell))
    xs = [lo + (hi - lo) * i / n for i in range(n + 1)]
    f = [eng.fx(tau, x, 0, True) > 0 for x in xs]
    d = [eng.fx(tau, x, 1, True) > 0 for x in xs]
    zeros = []
    for i in range(n):
        if f[i] != f[i + 1]:
            zeros.append(flow_bisect(eng, tau, xs[i], xs[i + 1], 0, tol))
        elif d[i] != d[i + 1]:
            turn = flow_bisect(eng, tau, xs[i], xs[i + 1], 1, 1e-6 if tol < 1e-6 else 1e-3)
            if (eng.fx(tau, turn) > 0) != f[i]:
                zeros += [flow_bisect(eng, tau, xs[i], turn, 0, tol), flow_bisect(eng, tau, turn, xs[i + 1], 0, tol)]
    return zeros


def flow_count(eng: flow_Engine, tau: float, lo: float, hi: float, cell: float = 0.1) -> int:
    """The number of real zeros of H(tau, .) in [lo, hi], without locating them."""
    return len(flow_real_zeros(eng, tau, lo, hi, cell, cell))


def flow_pair(eng: flow_Engine, tau: float, centre: float) -> tuple[float, float]:
    """The two real zeros within one unit of `centre`; (nan, nan) unless there are exactly two."""
    found = flow_real_zeros(eng, tau, centre - 1.0, centre + 1.0)
    return (found[0], found[1]) if len(found) == 2 else (math.nan, math.nan)


def flow_box_count(f, left: float, right: float, half_height: float, piece: float) -> int:
    """How many zeros the analytic f has in the rectangle left < Re x < right, |Im x| < half_height: the
    winding of f round its edge, the long sides sampled every `piece` before `winding` refines them."""
    k = int(math.ceil((right - left) / (8 * piece)))
    lower = [complex(left + (right - left) * i / k, -half_height) for i in range(k + 1)]
    upper = [complex(right - (right - left) * i / k, half_height) for i in range(k + 1)]
    return winding(f, lower + upper)


def flow_double_zero(eng: flow_Engine, tau: float, x: float) -> tuple[float, float, float]:
    """Newton's method for H = dH/dx = 0 in the two unknowns (tau, x), using dH/dtau = -d2H/dx2.
    Returns tau, x and the size of the last step."""
    last = math.inf
    for _ in range(25):
        if not (math.isfinite(tau + x) and abs(tau) < 4 and abs(x) < 1000):
            return math.nan, math.nan, math.inf
        h = [eng.val(tau, x, d) for d in range(4)]
        scale = max(abs(v) for v in h)
        h0, h1, h2, h3 = (v / scale for v in h)
        det = h1 * h3 - h2 * h2
        if det == 0:
            return math.nan, math.nan, math.inf
        d_tau, d_x = (h1 * h1 - h0 * h2) / det, (h1 * h2 - h0 * h3) / det
        tau, x = tau + d_tau, x + d_x
        last = abs(d_tau) + abs(d_x)
        if last < 1e-12:
            break
    return tau, x, last


def flow_complex_zero(eng: flow_Engine, tau: float, z: complex) -> complex:
    """Newton's method in the complex plane; nan if it wanders off."""
    for _ in range(40):
        if not (math.isfinite(tau) and abs(z) < 1000):
            return complex(math.nan, math.nan)
        slope = eng.cval(tau, z, 1)
        if slope == 0:
            return complex(math.nan, math.nan)
        step = eng.cval(tau, z) / slope
        z -= step
        if abs(step) < 1e-14:
            break
    return z


def flow_smooth(f, x, s: float, step: float = 0.125, reach: float = 9.0):
    """The heat equation run on f for a time s > 0, in ordinary floating point:
    (4 pi s)^(-1/2) * integral over real y of f(y) exp(-(x - y)^2 / (4s)) dy, at real or complex x.
    f falls like e^(-pi y / 4), which moves the peak of the integrand down by pi s / 2, so the window
    is centred there."""
    kernel = cmath.exp if isinstance(x, complex) else math.exp
    centre = x.real - PI * s / 2
    n = int(math.ceil(reach * math.sqrt(2 * s) / step))
    total = 0.0
    for i in range(-n, n + 1):
        y = centre + i * step
        total += f(y) * kernel(-(x - y) ** 2 / (4 * s))
    return total * step / math.sqrt(4 * PI * s)


def flow_xi_line(y: float) -> float:
    return xi(0.5 + 1j * y).real


def flow_second_route(tau_c: float, x_c: float, delta: float) -> bool:
    """A collision checked without the big integers. For tau < 0 the flow is Gaussian smoothing of xi, which
    ordinary floating point does well. Signs of the smoothed xi at x_c - 0.05, x_c, x_c + 0.05: True if at
    tau_c + delta the middle one is against both ends (two real zeros between them) and at tau_c - delta
    all three agree."""
    if not (math.isfinite(tau_c + x_c) and tau_c + delta < 0):
        return False
    before, after = ([flow_smooth(flow_xi_line, x_c + dx, -tau) > 0 for dx in (-0.05, 0.0, 0.05)] for tau in (tau_c + delta, tau_c - delta))
    return before[0] == before[2] != before[1] and after[0] == after[1] == after[2]


def flow_literature_h(t: float, z: float) -> float:
    """H_t(z) as the literature writes it, in ordinary floating point: the integral over v > 0 of
    e^(t v^2) Phi(v) cos(zv), Phi(v) = sum over n of (2 pi^2 n^4 e^(9v) - 3 pi n^2 e^(5v)) exp(-pi n^2 e^(4v))."""
    step, total = 1 / 128, 0.0
    for j in range(129):
        v = j * step
        dens = sum((2 * PI ** 2 * n ** 4 * math.exp(9 * v) - 3 * PI * n * n * math.exp(5 * v)) * math.exp(-PI * n * n * math.exp(4 * v)) for n in range(1, 9))
        total += (0.5 if j == 0 else 1.0) * dens * math.exp(t * v * v) * math.cos(z * v)
    return total * step


def flow_gap_variance(zeros: list[float]) -> float:
    """Variance of the neighbouring gaps, each multiplied by the local density of zeros
    log(x / 2 pi) / (2 pi) at its midpoint, so that an average gap is about 1."""
    g = [(b - a) * math.log(0.5 * (a + b) / (2 * PI)) / (2 * PI) for a, b in zip(zeros, zeros[1:])]
    mean = sum(g) / len(g)
    return sum((v - mean) ** 2 for v in g) / len(g)


def flow_gap_mean(zeros: list[float]) -> float:
    """The mean of the same scaled gaps: about 1 if the scaling is right."""
    g = [(b - a) * math.log(0.5 * (a + b) / (2 * PI)) / (2 * PI) for a, b in zip(zeros, zeros[1:])]
    return sum(g) / len(g)


def flow_closest(zeros: list[float]) -> tuple[float, int]:
    """The smallest neighbouring gap and the index of its lower zero."""
    return min((b - a, i) for i, (a, b) in enumerate(zip(zeros, zeros[1:])))


def flow_neighbour_sum(zeros: list[float], i: int, cut: float, tail: bool = True) -> float:
    """For the pair a = zeros[i], b = zeros[i + 1]: the sum of 1 / ((a - y)(b - y)) over every other zero y of
    the even function, that is the listed ones, the mirror images -y, and (the tail) beyond `cut` the smooth
    density log(y / 2 pi) / (2 pi) in place of the zeros not listed."""
    a, b = zeros[i], zeros[i + 1]
    total = sum(1 / ((a + y) * (b + y)) for y in zeros)
    total += sum(1 / ((a - y) * (b - y)) for k, y in enumerate(zeros) if k not in (i, i + 1))
    steps, span = 3200, 16.0  # y = cut * e^v, v from 0 to 16
    for k in range(steps if tail else 0):
        y = cut * math.exp((k + 0.5) * span / steps)
        total += y * (span / steps) * math.log(y / (2 * PI)) / (2 * PI) * (1 / ((a - y) * (b - y)) + 1 / ((a + y) * (b + y)))
    return total


def flow_run() -> None:
    # 256 binary places, 48 samples per unit of u, |u| <= 2: good for x up to about 115, where the aliased
    # point 2 pi 48 - x = 187 is still 1e-26 times smaller; C1a measures it
    eng = flow_Engine(256, 48, 2.0)
    top = flow_TOP

    # ------------------------------------------------------------------ C1: is the transform right?
    worst = 0.0
    for x in (0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0):
        want = flow_xi_line(x)
        worst = max(worst, abs(eng.val(0.0, x) - want) / abs(want))
    worst_c = 0.0
    for z in (10 + 0.3j, 40 - 0.5j, 76.4 + 0.2j, 78.3 + 0.5j, 110 + 1j):
        want_c = xi(0.5 + 1j * z)
        worst_c = max(worst_c, abs(eng.cval(0.0, z) - want_c) / abs(want_c))
    finer = flow_Engine(320, 96, 2.5)  # twice the samples, a longer range, 64 more bits
    moved = {"low": Fraction(0), "high": Fraction(0)}
    for x in (20.0, 60.0, 77.0, top, 110.0):
        for tau in (-0.32, 0.0, 0.5):
            for d in range(4):
                shift = abs(Fraction(eng.fx(tau, x, d), eng.one) / Fraction(finer.fx(tau, x, d), finer.one) - 1)
                key = "low" if x <= top else "high"
                moved[key] = max(moved[key], shift)
    plain, true80 = xi_from_phi(80.0), flow_xi_line(80.0)  # the same integral in ordinary floating point: rounding noise
    coarse = flow_Engine(256, 16, 2.0)
    coarse_off = abs(coarse.val(0.0, 80.0) - true80) / abs(true80)
    check(
        "C1a",
        worst < 1e-10 and worst_c < 1e-10 and moved["low"] < 1e-40 and moved["high"] < 1e-20 and abs(plain - true80) > 100 * abs(true80) and coarse_off > 100,
        f"the Fourier integral of Phi, summed in 256-bit integers, is xi(1/2 + ix): at x = 0, 10, ..., 110, where |xi| falls from 0.50 to {abs(eng.val(0.0, 110.0)):.1e}, "
        f"the largest relative gap from xi computed from gamma and zeta is {worst:.0e}, and at five points off the real axis {worst_c:.0e}. Doubling the sample points "
        f"and adding 64 bits moves H and its first three x-derivatives, at tau = -0.32, 0, 0.5, by at most {float(moved['low']):.0e} of themselves up to x = {top} and "
        f"{float(moved['high']):.0e} at x = 110 (that last test is the engine against a finer copy of itself: the first two derivatives are also tied to the motion "
        f"of the zeros in C2a, and through C1c to xi; the third only steers Newton's method). Controls at x = 80, where xi is {true80:.1e}: the same integral in ordinary floating point returns {plain:.0e}, "
        f"which is rounding noise, and the integers with a three times coarser step miss by {coarse_off:.0e} times the value",
    )

    zeros0 = flow_real_zeros(eng, 0.0, 0.0, top)
    from_list = max(abs(a - b) for a, b in zip(zeros0, flow_LISTED)) if len(zeros0) == 20 else 1.0
    from_xi = max(abs(z - bisect(flow_xi_line, z - 0.05, z + 0.05, 1e-12)) for z in zeros0)
    nudged = flow_real_zeros(eng, 0.001, 0.0, top)
    nudged_off = max(abs(a - b) for a, b in zip(nudged, flow_LISTED))
    check(
        "C1b",
        len(zeros0) == 20 and from_list < 5.0001e-5 and from_xi < 1e-9 and len(nudged) == 20 and nudged_off > 1e-3,
        f"H(0, x) has exactly 20 real zeros below {top}, from {zeros0[0]:.6f} to {zeros0[-1]:.6f}; each rounds to the listed height of a zero of zeta "
        f"(largest gap {from_list:.1e}, the list having four decimals) and sits within {from_xi:.0e} of a sign change of xi from gamma and zeta. "
        f"Control: after a flow of only tau = 0.001 the zeros miss the list by up to {nudged_off:.4f}",
    )

    # the flow is the heat equation: backward in tau it is Gaussian smoothing of xi with variance 2|tau|
    smooth_gap = wrong_gap = back_gap = 0.0
    for x in (5.0, 20.0, 50.0, top):
        scale = max(abs(eng.val(-0.32, x + dx)) for dx in (-0.4, 0.0, 0.4))
        smooth_gap = max(smooth_gap, abs(flow_smooth(flow_xi_line, x, 0.32) - eng.val(-0.32, x)) / scale)
        wrong_gap = max(wrong_gap, abs(flow_smooth(flow_xi_line, x, 0.30) - eng.val(-0.32, x)) / scale)
        scale = max(abs(flow_xi_line(x + dx)) for dx in (-0.4, 0.0, 0.4))
        back_gap = max(back_gap, abs(flow_smooth(lambda y: eng.val(0.5, y), x, 0.5) - flow_xi_line(x)) / scale)
    check(
        "C1c",
        smooth_gap < 1e-10 and back_gap < 1e-10 and wrong_gap > 0.01,
        f"multiplying Phi by e^(tau u^2) runs the heat equation dH/dtau = -d2H/dx2: at x = 5, 20, 50, {top}, smoothing xi (gamma and zeta, ordinary floating point, "
        f"no big integers) with a Gaussian of variance 2 * 0.32 gives H(-0.32, x) to within {smooth_gap:.0e} of its local size, and smoothing H(+0.5, .) with variance "
        f"2 * 0.5 gives xi back to within {back_gap:.0e}. Control: variance 2 * 0.30 against tau = -0.32 misses by {wrong_gap:.2f}",
    )

    lit_gap = lit_wrong = 0.0
    for tau, x in ((-0.32, 10.0), (0.0, 5.0), (0.5, 20.0), (-0.1, 15.0)):
        mine = eng.val(tau, x)
        lit_gap = max(lit_gap, abs(8 * flow_literature_h(4 * tau, 2 * x) - mine) / abs(mine))
        if tau:
            lit_wrong = max(lit_wrong, abs(8 * flow_literature_h(tau, 2 * x) - mine) / abs(mine))
    low_half = flow_real_zeros(eng, 0.5, 0.0, 26.0)  # the zeros of H(0.5, .) below 26, looked for again in the literature's integral
    lit_zeros = [x for x in low_half if flow_literature_h(2.0, 2 * (x - 1e-4)) * flow_literature_h(2.0, 2 * (x + 1e-4)) < 0]
    check(
        "C1d",
        lit_gap < 1e-9 and lit_wrong > 0.01 and len(low_half) == 3 and lit_zeros == low_half,
        f"in the literature's letters, H_t(z) = integral over v > 0 of e^(t v^2) Phi(v) cos(zv) with Phi(v) = sum (2 pi^2 n^4 e^(9v) - 3 pi n^2 e^(5v)) exp(-pi n^2 e^(4v)): "
        f"H(tau, x) = 8 H_t(z) with t = 4 tau and z = 2x, to {lit_gap:.0e} at (tau, x) = (-0.32, 10), (0, 5), (0.5, 20), (-0.1, 15), that integral done in ordinary "
        f"floating point; and the zeros of H(0.5, .) below 26, at {', '.join(f'{x:.4f}' for x in low_half)}, are sign changes of H_2(2x). "
        f"Control: with t = tau in place of 4 tau the two differ by up to {lit_wrong:.2f} of the value",
    )

    # ------------------------------------------------------------------ C2: forward in tau
    forward = {tau: flow_real_zeros(eng, tau, 0.0, top + 3) for tau in (0.0, 0.125, 0.5, 1.0, -0.2)}
    counts = [sum(z < top for z in forward[tau]) for tau in (0.0, 0.125, 0.5)]
    boxes = [flow_box_count(lambda z: eng.cval(tau, z), 0.0, top, 0.5, 0.125) for tau in (0.0, 0.125, 0.5)]
    # tau = 0 again without the big integers; the box starts at Re x = 1 to keep clear of s = 0 and 1, where the formula for xi is 0 times infinity
    box_xi = flow_box_count(lambda z: xi(0.5 + 1j * z), 1.0, top, 0.5, 0.125)
    drift_count = sum(z < top for z in forward[1.0])
    speed = [eng.val(0.0, x, 2) / eng.val(0.0, x, 1) for x in zeros0]  # dx/dtau of each zero, from dH/dtau = -d2H/dx2
    nudge = [flow_real_zeros(eng, side, 0.0, top) for side in (1e-4, -1e-4)]  # the same rates, by moving tau
    speed_gap = max(abs((a - b) / 2e-4 - v) for a, b, v in zip(nudge[0], nudge[1], speed)) if len(nudge[0]) == len(nudge[1]) == 20 else math.nan
    say("     tau: the first 21 real zeros")
    for tau in (-0.2, 0.0, 0.125, 0.5, 1.0):
        say(f"     {tau:+.3f}: " + " ".join(f"{z:.3f}" for z in forward[tau][:21]))
    check(
        "C2a",
        counts == [20, 20, 20] and boxes == [20, 20, 20] and box_xi == 20 and drift_count == 21 and max(speed) < 0 and speed_gap < 1e-5,
        f"forward, at tau = 0, 0.125, 0.5 (t = 0, 0.5, 2), the zeros stay real: real zeros below {top}: {counts[0]}, {counts[1]}, {counts[2]}; zeros of any kind in the box "
        f"0 < Re x < {top}, |Im x| < 1/2 (at tau = 0 the whole critical strip up to that height), counted by winding: {boxes[0]}, {boxes[1]}, {boxes[2]}, so none is off the "
        f"axis (at tau = 0, winding xi from gamma and zeta round the box from Re x = 1 gives {box_xi} too). Control: the count below a fixed height does not last, because "
        f"every zero also drifts down (at tau = 0 the rates dx/dtau = H''/H' run from {min(speed):.2f} to {max(speed):.2f}, and moving tau by 0.0001 either way gives the "
        f"same rates to {speed_gap:.0e}): the 21st sits at {forward[0.0][20]:.2f}, {forward[0.125][20]:.2f}, {forward[0.5][20]:.2f} and by tau = 1 at {forward[1.0][20]:.2f}, "
        f"inside ({drift_count} below {top})",
    )

    var = {tau: flow_gap_variance(forward[tau][:20]) for tau in forward}
    least = {tau: flow_closest(forward[tau][:20])[0] for tau in forward}
    mean_gap = {tau: flow_gap_mean(forward[tau][:20]) for tau in forward}
    check(
        "C2b",
        var[0.0] > 1.2 * var[0.125] > 1.2 * 1.2 * var[0.5] and least[0.0] < least[0.125] < least[0.5] and var[-0.2] > 1.2 * var[0.0] and least[-0.2] < least[0.0]
        and all(abs(mean_gap[tau] - 1) < 0.05 for tau in (-0.2, 0.0, 0.125, 0.5)),
        f"forward the zeros spread out: among the first 20, at tau = 0, 0.125, 0.5, the smallest gap grows, {least[0.0]:.3f}, {least[0.125]:.3f}, {least[0.5]:.3f}, and the "
        f"variance of the 19 gaps, each scaled by the local density of zeros, falls: {var[0.0]:.4f}, {var[0.125]:.4f}, {var[0.5]:.4f} (the scaled gaps average "
        f"{mean_gap[0.0]:.3f}, {mean_gap[0.125]:.3f}, {mean_gap[0.5]:.3f}, so the scaling is right). Control: backward, at tau = -0.2, "
        f"the smallest gap is {least[-0.2]:.3f} and the variance {var[-0.2]:.4f}",
    )

    # ------------------------------------------------------------------ C3: backward, the first collisions
    tau_steps = [-k / 50 for k in range(18)]
    scan = {tau: zeros0 if tau == 0 else flow_real_zeros(eng, tau, 0.0, top) for tau in tau_steps}
    say(f"     tau: real zeros below {top}, and the closest pair")
    for tau in tau_steps:
        g, i = flow_closest(scan[tau])
        say(f"     {tau:+.2f}: {len(scan[tau])}   zeros {i + 1} and {i + 2} at {scan[tau][i]:.4f}, {scan[tau][i + 1]:.4f}, gap {g:.4f}")
    n_scan = [len(scan[tau]) for tau in tau_steps]
    last_full = min(max(k for k in range(18) if n_scan[k] == 20), 15)  # the last step with all twenty real
    closing = [scan[tau][19] - scan[tau][18] for tau in tau_steps[:last_full + 1]]  # the gap between zeros 19 and 20
    # Newton for each collision starts from the closest pair at the step before it, moved on by 1.1 gap^2 / 8
    hits = []
    for k in (last_full, last_full + 1, last_full + 2):
        g, i = flow_closest(scan[tau_steps[k]])
        hits.append((i,) + flow_double_zero(eng, tau_steps[k] - 1.1 * g * g / 8, 0.5 * (scan[tau_steps[k]][i] + scan[tau_steps[k]][i + 1])))
    (i_1, tau_c, x_c, step_1), (i_2, tau_2, x_2, step_2), (i_3, tau_3, x_3, step_3) = hits
    size = max(abs(eng.val(tau_c, x_c + dx)) for dx in (-0.5, 0.5))
    touch = max(abs(eng.val(tau_c, x_c)), abs(eng.val(tau_c, x_c, 1))) / size
    around = [[flow_count(eng, tau + side, 0.0, top) for side in (1e-4, -1e-4)] for tau in (tau_c, tau_2, tau_3)]
    route = [flow_second_route(tau, x, 1e-9) for tau, x in ((tau_c, x_c), (tau_2, x_2), (tau_3, x_3))]
    route_off = flow_second_route(tau_c + 1e-8, x_c, 1e-9)
    check(
        "C3a",
        n_scan == [20] * 16 + [18, 16] and i_1 == 18 and step_1 < 1e-12 and touch < 1e-10 and all(a > b for a, b in zip(closing, closing[1:]))
        # the collision time and place are regression values; what confirms them from outside is the count either side and the second route
        and abs(tau_c + 0.318886) < 2e-6 and abs(x_c - 77.02664) < 2e-5 and around[0] == [20, 18] and route[0] and not route_off,
        f"backward in steps of 0.02 all 20 zeros below {top} stay real down to tau = {tau_steps[last_full]:.2f}, zeros 19 and 20 closing at every step from "
        f"{closing[0]:.4f} to {closing[-1]:.4f} apart; at -0.32 there are {n_scan[16]} real zeros, at -0.34 {n_scan[17]}. The first collision: zeros 19 and 20 "
        f"({zeros0[18]:.4f} and {zeros0[19]:.4f} at tau = 0) meet at x = {x_c:.4f} when tau_c = {tau_c:.6f}, t = 4 tau_c = {4 * tau_c:.6f}: there H and dH/dx are both "
        f"below {touch:.0e} of H half a unit away, with {around[0][0]} real zeros at tau_c + 0.0001 and {around[0][1]} at tau_c - 0.0001. Second route, no big integers: "
        f"xi from gamma and zeta, smoothed by a Gaussian of variance 2|tau| in ordinary floating point, has at the meeting point the sign opposite to its sign 0.05 "
        f"either side at tau_c + 1e-9, and the same sign at tau_c - 1e-9. Control: with tau_c moved by 1e-8 that test fails",
    )
    check(
        "C3b",
        # regression values, confirmed from outside by the counts either side and the second route
        (i_2, i_3) == (12, 8) and max(step_2, step_3) < 1e-12 and abs(tau_2 + 0.321317) < 2e-6 and abs(x_2 - 60.49072) < 2e-5
        and abs(tau_3 + 0.469477) < 2e-6 and abs(x_3 - 49.66423) < 2e-5 and around[1:] == [[18, 16], [16, 14]] and route[1] and route[2],
        f"the next two collisions among the first twenty: zeros 13 and 14 ({zeros0[12]:.4f}, {zeros0[13]:.4f}) meet at x = {x_2:.4f} when tau = {tau_2:.6f}, "
        f"t = {4 * tau_2:.6f}, only {tau_c - tau_2:.4f} further back than the first ({around[1][0]} real zeros below {top} at 0.0001 before, {around[1][1]} at 0.0001 after); "
        f"zeros 9 and 10 ({zeros0[8]:.4f}, {zeros0[9]:.4f}) meet at x = {x_3:.4f} when tau = {tau_3:.6f}, t = {4 * tau_3:.6f} ({around[2][0]} before, {around[2][1]} after). "
        f"The second route puts both times within 1e-9 of these",
    )

    # ------------------------------------------------------------------ C4: just after and just before
    eps = 0.001
    below, above = tau_c - eps, tau_c + eps
    real_below = flow_real_zeros(eng, below, 0.0, top)
    real_above = flow_real_zeros(eng, above, 0.0, top)
    pair = flow_pair(eng, above, x_c)
    zc = flow_complex_zero(eng, below, complex(x_c, math.sqrt(2 * eps)))
    depth = abs(eng.cval(below, zc)) / abs(eng.cval(below, zc.real))
    box_all = flow_box_count(lambda z: eng.cval(below, z), 0.0, top, 0.5, 0.125)
    same_search = flow_complex_zero(eng, above, complex(x_c, math.sqrt(2 * eps)))  # control: the same search before the collision
    check(
        "C4a",
        len(real_below) == 18 and len(real_above) == 20 and abs(zc.imag - 0.044737) < 2e-5 and abs(zc.real - 77.028596) < 2e-5 and depth < 1e-9
        and box_all == 20 and abs(pair[1] - pair[0] - 0.089411) < 2e-5 and abs(same_search.imag) < 1e-12 and abs(same_search.real - pair[1]) < 1e-9,
        f"at tau = tau_c - 0.001 there are {len(real_below)} real zeros below {top}, two fewer, and Newton's method finds the missing pair at "
        f"{zc.real:.5f} +- {abs(zc.imag):.5f}i (a double zero opening sideways predicts +- sqrt(2 * 0.001) = {math.sqrt(2 * eps):.5f}i), where |H| is {depth:.0e} of |H| at the "
        f"real point between them; the box |Im x| < 1/2 still holds {box_all} zeros, 18 real and 2 not. At tau = tau_c + 0.001 all {len(real_above)} are real and the pair "
        f"sits at {pair[0]:.5f} and {pair[1]:.5f}, {pair[1] - pair[0]:.5f} apart (predicted sqrt(8 * 0.001) = {math.sqrt(8 * eps):.5f}). Control: the same Newton search "
        f"run at tau_c + 0.001 ends on the real axis, at {same_search.real:.5f}",
    )

    local = {(tau, hh): flow_box_count(lambda z: eng.cval(tau, z), x_c - 0.5, x_c + 0.5, hh, 0.0125) for tau in (below, above) for hh in (0.5, 0.02)}
    grid = [x_c + 0.05 * k for k in range(-6, 7)]  # the second route, at 13 points across the meeting point
    route_gap, flips = 0.0, {}
    for tau in (below, above):
        mine = [eng.val(tau, x) for x in grid]
        other = [flow_smooth(flow_xi_line, x, -tau) for x in grid]
        route_gap = max(route_gap, max(abs(a - b) for a, b in zip(mine, other)) / max(abs(a) for a in mine))
        flips[tau] = sum((a > 0) != (b > 0) for a, b in zip(other, other[1:]))
    route_depth = abs(flow_smooth(flow_xi_line, zc, -below)) / abs(flow_smooth(flow_xi_line, zc.real, -below))  # the smoothing, continued off the axis
    check(
        "C4b",
        local == {(below, 0.5): 2, (below, 0.02): 0, (above, 0.5): 2, (above, 0.02): 2} and route_gap < 1e-9 and flips == {below: 0, above: 2} and route_depth < 1e-8,
        f"the same seen two other ways. By winding: a box one unit wide round the meeting point holds {local[(above, 0.5)]} zeros at tau_c + 0.001 and {local[(below, 0.5)]} "
        f"at tau_c - 0.001 if it is 1 tall, but {local[(above, 0.02)]} and then {local[(below, 0.02)]} if it is 0.04 tall, too thin to hold the pair once it has left the axis. "
        f"By the second route: the smoothed xi agrees with the integers at 13 points across the meeting point to {route_gap:.0e} of the local size, changes sign "
        f"{flips[above]} times before and {flips[below]} times after, and continued off the axis to the complex zero is {route_depth:.0e} of its value at the real point beneath",
    )

    # ------------------------------------------------------------------ C5: the law of the gap near the collision
    rows = []
    for d in (0.0005, 0.001, 0.002, 0.004):
        a, b = flow_pair(eng, tau_c + d, x_c)
        w = flow_complex_zero(eng, tau_c - d, complex(x_c, math.sqrt(2 * d)))
        rows.append((d, (b - a) ** 2 / d, 4 * w.imag ** 2 / d, ((b - a) ** 2 + 4 * w.imag ** 2) / (2 * d)))
    far = (zeros0[19] - zeros0[18]) ** 2 / -tau_c
    say("     tau - tau_c: gap^2 / (tau - tau_c) on the real side, on the complex side, slope through the collision")
    for row in rows:
        say(f"     {row[0]:.4f}: {row[1]:.5f}  {row[2]:.5f}  {row[3]:.7f}")
    check(
        "C5",
        # 6.5040: regression value, with no second route (it only illustrates that the law is local)
        all(abs(r[1] - 8) < 6 * r[0] and abs(r[2] - 8) < 6 * r[0] and r[1] < 8 < r[2] for r in rows) and abs(rows[1][3] - 8) < 1e-4 and abs(far - 6.5040) < 1e-3,
        f"near the collision the squared gap is 8 (tau - tau_c): at tau - tau_c = 0.0005, 0.001, 0.002, 0.004 the ratio gap^2 / (tau - tau_c) is "
        f"{', '.join(f'{r[1]:.4f}' for r in rows)}; past the collision, with the gap now 2bi, (2b)^2 / (tau_c - tau) is {', '.join(f'{r[2]:.4f}' for r in rows)}; "
        f"the squared difference of the two zeros runs straight through zero with slope {rows[1][3]:.5f} (from tau_c - 0.001 to tau_c + 0.001). "
        f"Control: the law is local; over the whole way from tau = 0 the same ratio is {far:.2f}",
    )

    # ------------------------------------------------------------------ C6: against the isolated-pair estimate
    gaps0 = [zeros0[i + 1] - zeros0[i] for i in (18, 12, 8)]
    est = [-g * g / 8 for g in gaps0]
    actual = [tau_c, tau_2, tau_3]
    late = [100 * (a / e - 1) for a, e in zip(actual, est)]
    at_est = flow_real_zeros(eng, est[0], 0.0, top)
    still = at_est[19] - at_est[18] if len(at_est) == 20 else math.nan
    check(
        "C6a",
        # 23.00, 16.61, 20.06, 0.6766: regression values; they follow from the gaps at tau = 0 and the collision times checked in C3
        abs(late[0] - 23.00) < 0.05 and abs(late[1] - 16.61) < 0.05 and abs(late[2] - 20.06) < 0.05 and abs(still - 0.6766) < 1e-3 and est[0] > est[1] > est[2]
        and actual[0] > actual[1] > actual[2],
        f"the estimate -g^2/8, exact for a pair alone, is early for these. Zeros 19, 20 start g = {gaps0[0]:.5f} apart: estimate {est[0]:.5f}, actual {actual[0]:.5f}, "
        f"{late[0]:.1f}% further back; zeros 13, 14, g = {gaps0[1]:.5f}: estimate {est[1]:.5f}, actual {actual[1]:.5f}, {late[1]:.1f}% further; zeros 9, 10, g = {gaps0[2]:.5f}: "
        f"estimate {est[2]:.5f}, actual {actual[2]:.5f}, {late[2]:.1f}% further. The order is as estimated, but the lead of the first over the second shrinks from "
        f"{est[0] - est[1]:.4f} to {actual[0] - actual[1]:.4f}. Control: at the estimated time, tau = {est[0]:.4f}, nothing has met: all {len(at_est)} zeros are real and "
        f"zeros 19 and 20 are still {still:.3f} apart",
    )

    rate = 2 * gaps0[0] * (speed[19] - speed[18])  # d(gap^2)/dtau for zeros 19 and 20 at tau = 0
    low35 = flow_real_zeros(eng, 0.0, 0.0, flow_HIGH)
    push = 4 * gaps0[0] ** 2 * flow_neighbour_sum(low35, 18, flow_HIGH) if len(low35) == 35 else math.nan
    push_listed = 4 * gaps0[0] ** 2 * flow_neighbour_sum(low35, 18, flow_HIGH, False) if len(low35) == 35 else math.nan
    check(
        "C6b",
        abs(rate - 5.2512) < 1e-3 and abs(8 - push - rate) < 0.002 and abs(8 - push_listed - rate) > 0.1,  # 5.2512: regression value
        f"the direction of that error, explained at the start of the motion. At tau = 0 the squared gap g^2 of zeros 19, 20 changes at {rate:.4f} per unit tau, not at the 8 of a pair alone "
        f"(from dx/dtau = H''/H' at each zero), and the shortfall {8 - rate:.4f} is the push of the neighbours, 4 g^2 * sum of 1/((a - y)(b - y)) over the other zeros y, "
        f"which comes to {push:.4f} (33 zeros below {flow_HIGH:.0f}, their mirror images, a smooth density beyond). Control: without the part beyond {flow_HIGH:.0f} "
        f"the sum gives {push_listed:.4f} and the match is lost. This accounts for the rate at the start, not for the whole delay: the push changes as the zeros move "
        f"(held at its starting value it would put the collision at {-gaps0[0] ** 2 / rate:.4f}, past the true {actual[0]:.4f})",
    )

    # ------------------------------------------------------------------ C7: higher up, sooner
    # Newton starts 12% beyond the lone-pair estimate and a little above the midpoint, since collisions come late
    # and high; what it converges to is then tested by the counts either side and by the second route
    found = []
    for i in (33, 26, 23):  # zeros 34 and 35, 27 and 28, 24 and 25
        a, b = low35[i], low35[i + 1]
        t_hit, x_hit, step_hit = flow_double_zero(eng, -1.12 * (b - a) ** 2 / 8, 0.5 * (a + b) + 0.15 * (b - a))
        n_hit = [flow_count(eng, t_hit + side, 0.0, flow_HIGH) for side in (5e-4, -5e-4)]
        found.append((a, b, t_hit, x_hit, step_hit, n_hit, flow_second_route(t_hit, x_hit, 1e-9)))
    check(
        "C7a",
        # regression values, confirmed from outside by the counts either side and the second route
        abs(found[0][2] + 0.096140) < 2e-6 and abs(found[1][2] + 0.220269) < 2e-6 and abs(found[2][2] + 0.285967) < 2e-6 and all(f[4] < 1e-12 and f[6] for f in found)
        and [f[5] for f in found] == [[35, 33], [33, 31], [31, 29]] and found[0][2] > found[1][2] > found[2][2] > tau_c,
        f"which collision comes first depends on how high one looks, and higher is sooner. Of the 35 zeros below {flow_HIGH:.0f} the first to meet are "
        f"{found[0][0]:.4f} and {found[0][1]:.4f}, at x = {found[0][3]:.4f} when tau = {found[0][2]:.6f} (t = {4 * found[0][2]:.6f}), then {found[1][0]:.4f} and {found[1][1]:.4f} "
        f"at {found[1][2]:.6f} (t = {4 * found[1][2]:.6f}), then {found[2][0]:.4f} and {found[2][1]:.4f} at {found[2][2]:.6f} (t = {4 * found[2][2]:.6f}), all three before "
        f"the first collision below {top}: real zeros below {flow_HIGH:.0f} at 0.0005 before and after each, {', '.join(f'{f[5][0]} and {f[5][1]}' for f in found)}. "
        f"The second route puts all three times within 1e-9 of these",
    )

    tall = flow_Engine(640, 160, 2.5)  # 640 binary places for heights near 415, where xi is 1e-139
    tall_gap = max(abs(tall.val(0.0, x) - flow_xi_line(x)) / abs(flow_xi_line(x)) for x in (300.0, 400.0, 415.0))
    a415, b415 = flow_pair(tall, 0.0, 415.5)
    t415, x415, step415 = flow_double_zero(tall, -1.05 * (b415 - a415) ** 2 / 8, 0.5 * (a415 + b415))
    # all the zeros below 417: the 256-bit integers reach 113, the 640-bit ones take over from there
    n415 = [flow_count(eng, tau, 0.0, flow_HIGH) + flow_count(tall, tau, flow_HIGH, flow_FAR, 0.3) for tau in (0.0, t415 + 0.0002)]
    near415 = [flow_count(tall, tau, 414.0, flow_FAR) for tau in (t415 + 0.0002, t415 - 0.0002)]
    route415 = [flow_second_route(t415 + shift, x415, 1e-9) for shift in (0.0, 1e-8)]
    check(
        "C7b",
        # 415.0188, 415.4552: the 212th and 213th zeros of zeta (external, from memory); the time is a regression value, confirmed by the second route
        tall_gap < 1e-9 and abs(a415 - 415.0188) < 1e-3 and abs(b415 - 415.4552) < 1e-3 and abs(t415 + 0.024768) < 2e-6 and step415 < 1e-11
        and n415 == [213, 213] and near415 == [2, 0] and route415 == [True, False] and t415 > found[0][2],
        f"higher still, sooner still: of the 213 zeros below {flow_FAR:.0f} (640-bit integers, within {tall_gap:.0e} of xi from gamma and zeta at 300, 400, 415) the first "
        f"to meet are {a415:.4f} and {b415:.4f}, {b415 - a415:.4f} apart at tau = 0, at x = {x415:.4f} when tau = {t415:.6f}, t = {4 * t415:.6f}: {n415[0]} real zeros below "
        f"{flow_FAR:.0f} at tau = 0 and still {n415[1]} at tau = {t415 + 0.0002:.6f}; between 414 and {flow_FAR:.0f}, {near415[0]} then and {near415[1]} at tau = "
        f"{t415 - 0.0002:.6f}. The second route puts the time within 1e-9 of this; control: moved by 1e-8 it fails that test",
    )

    # ------------------------------------------------------------------ C7c: the windows above each end just above a pair
    a169, b169 = flow_pair(tall, 0.0, 169.5)
    t169, x169, step169 = flow_double_zero(tall, -1.1 * (b169 - a169) ** 2 / 8, 0.5 * (a169 + b169) + 0.1 * (b169 - a169))
    n169 = [flow_count(eng, tau, 0.0, flow_HIGH) + flow_count(tall, tau, flow_HIGH, 170.5, 0.3) for tau in (0.0, t169 + 0.0002)]
    near169 = [flow_count(tall, tau, 168.0, 170.5) for tau in (t169 + 0.0002, t169 - 0.0002)]
    route169 = [flow_second_route(t169 + shift, x169, 1e-9) for shift in (0.0, 1e-8)]
    # and nothing between the two windows meets before the pair near 111 does: the zeros from 113 to 168.5, either side of that collision
    mid169 = [flow_count(tall, found[0][2] + side, flow_HIGH, 168.5, 0.3) for side in (2e-4, -2e-4)]
    check(
        "C7c",
        abs(a169 - 169.0945) < 1e-3 and abs(b169 - 169.9120) < 1e-3  # the 63rd and 64th zeros of zeta, from the tables (external, from memory)
        and step169 < 1e-11 and n169 == [64, 64] and near169 == [2, 0] and route169 == [True, False] and found[0][2] < t169 < t415
        and mid169 == [27, 27],
        f"the three windows each end just above the pair that meets first in them, and between the windows other pairs take the lead. Zeros 63 and 64, at {a169:.4f} and "
        f"{b169:.4f}, meet at x = {x169:.4f} when tau = {t169:.6f}, t = {4 * t169:.6f}: sooner than the pair near 111 (t = {4 * found[0][2]:.6f}) and later than the pair "
        f"near 415 (t = {4 * t415:.6f}). All {n169[0]} zeros below 170.5 are real at tau = 0 and still {n169[1]} at tau = {t169 + 0.0002:.6f}; between 168 and 170.5 there are "
        f"{near169[0]} then and {near169[1]} at tau = {t169 - 0.0002:.6f}. The second route puts the time within 1e-9 of this; control: moved by 1e-8 it fails that test. "
        f"The {mid169[0]} zeros between 113 and 168.5 are all real at tau = {found[0][2] + 2e-4:.6f} and still {mid169[1]} at tau = {found[0][2] - 2e-4:.6f}, either side of the collision "
        f"near 111, so no pair between the two windows meets first. So the lower bound t = {4 * found[0][2]:.4f} is what a search gets if it stops between heights 112 and 169, and no further",
    )


def section_flow() -> None:
    """The checks of flow_run. Each builds on the numbers before it, so a wrong number early on can make a
    later step raise; then the checks not yet reported are failed, and the program goes on."""
    start = len(RESULTS)
    try:
        flow_run()
    except Exception as err:
        for name in flow_NAMES[len(RESULTS) - start:]:
            check(name, False, f"not computed: an earlier step raised {type(err).__name__} ({err})")


# ====================================================================================================
# section D: zeros

TITLE_ZEROS = "D. The zeros themselves: every one up to height 30000, counted, spaced and averaged"

zeros_T = 30000.0  # zeros are found for 0 < t <= zeros_T
zeros_H = 0.1  # step of the grid on which Z is sampled
zeros_T_LOW = 200.0  # below this height Z comes from core.zeta, above it from the Riemann-Siegel formula

# The Riemann-Siegel remainder is (-1)^(N-1) a^(-1/2) [C_0(p) + C_1(p)/a + ... + C_6(p)/a^6], where a = sqrt(t/2pi),
# N = floor(a), p = a - N, and every C_k is a combination of derivatives of
#     Psi(p) = cos(2 pi (p^2 - p - 1/16)) / cos(2 pi p).
# Row k lists C_k as entries (m, e, numerator, denominator), each meaning (numerator/denominator) pi^e Psi^(m)(p).
# The rows were derived offline in exact rational arithmetic from the saddle-point expansion; rows 0 to 4 are the
# classical ones. Check D1 tests every row against core.zeta.
zeros_RS_TABLE = [
    [(0, 0, 1, 1)],
    [(3, -2, -1, 96)],
    [(6, -4, 1, 18432), (2, -2, 1, 64)],
    [(9, -6, -1, 5308416), (5, -4, -1, 3840), (1, -2, -1, 64)],
    [(12, -8, 1, 2038431744), (8, -6, 11, 5898240), (4, -4, 19, 24576), (0, -2, 1, 128)],
    [(15, -10, -1, 978447237120), (11, -8, -7, 849346560), (7, -6, -901, 82575360), (3, -4, -5, 3072)],
    [(18, -12, 1, 563585608581120), (14, -10, 17, 652298158080), (10, -8, 18889, 237817036800), (6, -6, 367, 7864320), (2, -4, 5, 2048)],
]


def zeros_theta(t: float) -> float:
    """Riemann-Siegel theta from its asymptotic series. For 10 <= t <= 30000 it agrees with core.theta to
    about 1e-11, which is the rounding of either."""
    u = 1 / (t * t)
    return 0.5 * t * (math.log(t / (2 * PI)) - 1) - PI / 8 + (1 / 48 + (7 / 5760 + (31 / 80640 + 127 / 430080 * u) * u) * u) / t


def zeros_psi_taylor(n_terms: int = 36, m: int = 256) -> list[float]:
    """Coefficients of x^(2j) in Psi(1/2 + x) = cos(2 pi x^2 + 3 pi/8) / cos(2 pi x), by Cauchy's formula on the
    unit circle. Psi is entire, even, and real on the real axis, so a quarter of the circle is enough. (Dividing
    the two power series instead would lose every digit: 1/cos has poles at x = +-1/4 that the numerator cancels.)"""
    quarter = [cmath.exp(2j * PI * (k + 0.5) / m) for k in range(m // 4)]
    values = [cmath.cos(2 * PI * x * x + 3 * PI / 8) / cmath.cos(2 * PI * x) for x in quarter]
    return [4 / m * sum((v * x ** (-2 * j)).real for x, v in zip(quarter, values)) for j in range(n_terms)]


def zeros_rs_series(table: list, n_keep: int = 32) -> list[list[float]]:
    """For each row of the table, the Taylor coefficients of C_k(1/2 + x): entry i is the coefficient of x^i.
    Powers up to x^31 leave less than 1e-13 for |x| <= 1/2."""
    q = zeros_psi_taylor()
    series = []
    for terms in table:
        co = [0.0] * n_keep
        for m, e, num, den in terms:
            weight = num / den * PI ** e
            for j in range((m + 1) // 2, (m + n_keep + 1) // 2):
                n = 2 * j - m  # x^(2j) differentiated m times lands on x^n, with factor (2j)!/n!
                co[n] += weight * q[j] * math.prod(range(n + 1, 2 * j + 1))
        series.append(co)
    return series


def zeros_make_z(t_max: float, table: list, last: int = 6, low: float = zeros_T_LOW):
    """The function Z(t) for 0 <= t <= t_max: core.zeta below the height `low`, above it the Riemann-Siegel
    formula with the corrections C_0 .. C_last. With a = sqrt(t/2pi), N = floor(a), x = a - N - 1/2 (so p = x + 1/2),
        Z(t) = 2 sum_{n <= N} n^(-1/2) cos(theta(t) - t log n) + (-1)^(N-1) a^(-1/2) sum_k C_k(p) a^(-k).
    For each N the whole remainder is one polynomial in x, built here by expanding a^(-k-1/2) = (N + 1/2 + x)^(-k-1/2)
    (fifteen terms of that expansion are enough from N = 3 on)."""
    series = [[(i, c) for i, c in enumerate(co) if c] for co in zeros_rs_series(table)[:last + 1]]
    n_max = int(math.sqrt(t_max / (2 * PI))) + 1
    terms = [(math.log(n), 2 / math.sqrt(n)) for n in range(1, n_max + 1)]
    prefixes = [terms[:n] for n in range(n_max + 1)]
    remainders: list[list[float]] = [[] for _ in range(n_max + 1)]
    degree = 36
    for n in range(int(math.sqrt(low / (2 * PI))), n_max + 1):
        mid = n + 0.5
        poly = [0.0] * degree
        for k, co in enumerate(series):
            b = mid ** (-k - 0.5)  # binomial series: (mid + x)^(-k-1/2) = sum_j b_j x^j, with |x/mid| <= 1/7
            for j in range(15):
                for i, c in co:
                    if i + j < degree:
                        poly[i + j] += c * b
                b *= (-k - 0.5 - j) / ((j + 1) * mid)
        remainders[n] = [c if n & 1 else -c for c in reversed(poly)]
    inv2pi = 1 / (2 * PI)
    cos, sqrt = math.cos, math.sqrt

    def z(t: float) -> float:
        if t < low:
            return (cmath.exp(1j * theta(t)) * zeta(complex(0.5, t))).real
        a = sqrt(t * inv2pi)
        n = int(a)
        x = a - n - 0.5
        th = zeros_theta(t)
        s = 0.0
        for log_n, w in prefixes[n]:
            s += w * cos(th - t * log_n)
        r = 0.0
        for c in remainders[n]:
            r = r * x + c
        return s + r

    return z


def zeros_cubic_root(ym: float, y0: float, y1: float, y2: float) -> float:
    """The root in (0, 1) of the cubic through (-1, ym), (0, y0), (1, y1), (2, y2), where y0 and y1 differ in sign."""
    c3 = (y2 - 3 * y1 + 3 * y0 - ym) / 6
    c2 = (y1 - 2 * y0 + ym) / 2
    c1 = y1 - y0 - c2 - c3
    u = y0 / (y0 - y1)
    for _ in range(4):
        slope = c1 + u * (2 * c2 + 3 * c3 * u)
        if slope == 0:
            break
        u -= (y0 + u * (c1 + u * (c2 + u * c3))) / slope
    return u


def zeros_refine(z, a: float, fa: float, b: float, fb: float, guess: float | None = None, tol: float = 2e-9) -> float:
    """The zero of z in [a, b], given values of opposite sign at the ends. Secant steps through the two latest
    points, replaced by the midpoint whenever a step leaves the bracket. It stops when the next step is shorter
    than tol; the point it then returns is far closer than tol (what limits it is the rounding noise in z)."""
    x0, f0 = (a, fa) if abs(fa) < abs(fb) else (b, fb)
    x1 = guess if guess is not None and a < guess < b else a - fa * (b - a) / (fb - fa)
    for _ in range(100):
        if abs(x1 - x0) < tol:
            break
        if not a < x1 < b:
            x1 = 0.5 * (a + b)
        f1 = z(x1)
        if f1 == 0:
            break
        if (f1 > 0) == (fa > 0):
            a, fa = x1, f1
        else:
            b, fb = x1, f1
        x0, f0, x1 = x1, f1, (x1 - f1 * (x1 - x0) / (f1 - f0) if f1 != f0 else 0.5 * (a + b))
    return min(max(x1, a), b)


def zeros_dip(z, a: float, m: float, b: float, fm: float, sign: float) -> tuple[float, float]:
    """sign*z is positive at a < m < b and lowest at m. Golden-section search for its minimum between a and b,
    stopping as soon as sign*z turns negative (two zeros are then bracketed) or the bracket has closed.
    Returns (t, sign*z(t)) at the lowest point seen."""
    g = 0.5 * (3 - math.sqrt(5))
    for _ in range(100):
        if fm < 0 or b - a < 1e-9:
            break
        if b - m > m - a:
            x = m + g * (b - m)
            fx = sign * z(x)
            if fx < fm:
                a, m, fm = m, x, fx
            else:
                b = x
        else:
            x = m - g * (m - a)
            fx = sign * z(x)
            if fx < fm:
                b, m, fm = m, x, fx
            else:
                a = x
    return m, fm


def zeros_find(z, t_max: float, h: float):
    """Every zero of z on (0, t_max] that a grid of step h can see: a sign change between neighbouring grid
    points is one zero; a dip of |z| between grid points of one sign is searched for a pair of zeros.
    Returns (grid values, zeros in order, the pairs found in dips, the dips that did not reach zero)."""
    n = int(round(t_max / h))
    grid = [z(j * h) for j in range(n + 1)]
    found, pairs, misses = [], [], []
    for j in range(1, n + 1):
        f0, f1 = grid[j - 1], grid[j]
        if (f0 > 0) != (f1 > 0):
            guess = (j - 1 + zeros_cubic_root(grid[j - 2], f0, f1, grid[j + 1])) * h if 2 <= j < n else None
            found.append(zeros_refine(z, (j - 1) * h, f0, j * h, f1, guess))
        elif j < n:
            f2 = grid[j + 1]
            if (f1 > 0) == (f2 > 0) and abs(f1) < abs(f0) and abs(f1) <= abs(f2):
                sign = 1.0 if f1 > 0 else -1.0
                tm, vm = zeros_dip(z, (j - 1) * h, j * h, (j + 1) * h, abs(f1), sign)
                if vm < 0:
                    pair = (zeros_refine(z, (j - 1) * h, f0, tm, sign * vm), zeros_refine(z, tm, sign * vm, (j + 1) * h, f2))
                    found.extend(pair)
                    pairs.append(pair)
                else:
                    misses.append((tm, sign * vm))
    found.sort()
    return grid, found, pairs, misses


def zeros_backlund(t: float, pieces: int = 24, tol: float = 0.3) -> tuple[float, int]:
    """S(t) = (1/pi) arg zeta(1/2 + it), the argument continued from 2 + it, where it is the principal one
    because Re zeta(2 + it) > 0, along the horizontal segment to 1/2 + it; the segment is cut until the
    argument moves by less than tol between neighbours. Uses core.zeta only.
    Returns (S, number of zeta evaluations)."""
    count = [0]

    def f(sigma: float) -> complex:
        count[0] += 1
        return zeta(complex(sigma, t))

    def turn(a: float, fa: complex, b: float, fb: complex, depth: int) -> float:
        d = cmath.phase(fb / fa)
        if abs(d) < tol or depth >= 30:
            return d
        m = 0.5 * (a + b)
        fm = f(m)
        return turn(a, fa, m, fm, depth + 1) + turn(m, fm, b, fb, depth + 1)

    sig = [2 - 1.5 * k / pieces for k in range(pieces + 1)]
    vals = [f(s) for s in sig]
    total = cmath.phase(vals[0])
    for k in range(pieces):
        total += turn(sig[k], vals[k], sig[k + 1], vals[k + 1], 0)
    return total / PI, count[0]


def zeros_mean_s(found: list[float], a: float, b: float) -> float:
    """The average over a <= t <= b of [number of listed zeros up to t] - theta(t)/pi - 1."""
    area = sum(b - max(g, a) for g in found if g <= b)
    n = 400
    h = (b - a) / n
    smooth = (zeros_theta(a) + zeros_theta(b) + 4 * sum(zeros_theta(a + (2 * k + 1) * h) for k in range(n // 2))
              + 2 * sum(zeros_theta(a + 2 * k * h) for k in range(1, n // 2))) * h / 3
    return (area - smooth / PI) / (b - a) - 1


def zeros_wigner_cdf(s: float) -> float:
    """Distribution function of the Wigner surmise p(s) = (32/pi^2) s^2 exp(-4 s^2/pi)."""
    return math.erf(2 * s / math.sqrt(PI)) - (4 * s / PI) * math.exp(-4 * s * s / PI)


def zeros_poisson_cdf(s: float) -> float:
    return 1 - math.exp(-s)


def zeros_ks(ordered: list[float], cdf) -> float:
    """Kolmogorov-Smirnov distance between a sorted sample and a distribution function."""
    n = len(ordered)
    worst = 0.0
    for i, v in enumerate(ordered):
        f = cdf(v)
        worst = max(worst, f - i / n, (i + 1) / n - f)
    return worst


def zeros_gap_stats(heights: list[float]) -> dict:
    """Statistics of the normalised gaps d_n = (g_(n+1) - g_n) log(g_n/2pi)/(2pi) of an increasing list."""
    d = [(heights[i + 1] - heights[i]) * math.log(heights[i] / (2 * PI)) / (2 * PI) for i in range(len(heights) - 1)]
    n = len(d)
    mean = sum(d) / n
    ordered = sorted(d)
    return {
        "n": n,
        "mean": mean,
        "var": sum((x - mean) ** 2 for x in d) / n,
        "below": sum(1 for x in d if x < 0.25) / n,
        "min": ordered[0],
        "max": ordered[-1],
        "ks_poisson": zeros_ks(ordered, zeros_poisson_cdf),
        "ks_wigner": zeros_ks(ordered, zeros_wigner_cdf),
        "gaps": d,
    }


def zeros_heights(counts: list[float]) -> list[float]:
    """Heights t at which the smooth count theta(t)/pi + 1 takes the given increasing values (all above 0):
    points placed at these heights have the same density as the zeros."""
    out = []
    t = 15.0
    for y in counts:
        target = PI * (y - 1)
        for _ in range(50):
            step = (zeros_theta(t) - target) / (0.5 * math.log(t / (2 * PI)))
            t -= step
            if abs(step) < 1e-10:
                break
        out.append(t)
    return out


def zeros_simpson(vals: list[float], h: float, j0: int, j1: int) -> float:
    """Simpson's rule over vals[j0..j1] with step h (j1 - j0 even)."""
    return (vals[j0] + vals[j1] + 4 * sum(vals[j0 + 1:j1:2]) + 2 * sum(vals[j0 + 2:j1 - 1:2])) * h / 3


def zeros_fit_line(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Least squares: (c0, c1) with ys ~ c0 + c1 xs."""
    n, sx, sy = len(xs), sum(xs), sum(ys)
    c1 = (n * sum(x * y for x, y in zip(xs, ys)) - sx * sy) / (n * sum(x * x for x in xs) - sx * sx)
    return (sy - c1 * sx) / n, c1


def zeros_two_lines(t_max: float):
    """A function t -> (|zeta(3/4 + it)|^2, |zeta(1 + it)|^2) for 0 < t <= t_max, by Euler-Maclaurin summation
    with t/2 + 20 terms, the powers n^(-it) shared between the two lines. Relative error below 1e-7 (check D8)."""
    n_max = int(t_max / 2) + 22
    logs = [math.log(n) for n in range(1, n_max + 1)]
    weights = [[n ** -sigma for n in range(1, n_max + 1)] for sigma in (0.75, 1.0)]
    bern = [(1 / 6) / 2, (-1 / 30) / 24, (1 / 42) / 720, (-1 / 30) / 40320, (5 / 66) / 3628800]  # B_2k / (2k)!
    cexp = cmath.exp

    def both(t: float) -> tuple[float, float]:
        big = int(t / 2) + 20
        phases = [cexp(-1j * t * log_n) for log_n in logs[:big - 1]]
        log_big = logs[big - 1]
        out = []
        for sigma, w in zip((0.75, 1.0), weights):
            s = complex(sigma, t)
            total = sum(map(operator.mul, w, phases)) + cexp((1 - s) * log_big) / (s - 1) + 0.5 * cexp(-s * log_big)
            term = s * cexp((-s - 1) * log_big)
            for k, b in enumerate(bern):
                total += b * term
                term *= (s + 2 * k + 1) * (s + 2 * k + 2) / (big * big)
            out.append(abs(total) ** 2)
        return out[0], out[1]

    return both


zeros_NAMES = ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12"]


def zeros_run() -> None:
    T, H = zeros_T, zeros_H
    z = zeros_make_z(T, zeros_RS_TABLE)

    # ---- D1: the fast Z against core.zeta
    def exact(t: float) -> complex:
        return cmath.exp(1j * theta(t)) * zeta(complex(0.5, t))

    low = [200.0 + 200.0 * (k + 0.37) / 16 for k in range(16)]
    low_exact = [exact(t).real for t in low]
    by_terms = []
    for last in range(7):
        z_few = zeros_make_z(400.0, zeros_RS_TABLE, last)
        by_terms.append(max(abs(z_few(t) - e) for t, e in zip(low, low_exact)))
    spread = [200.0 * (T / 200.0) ** ((k + 0.5) / 24) for k in range(24)]
    spread_exact = [exact(t) for t in spread]
    err_all = max(abs(z(t) - e.real) for t, e in zip(spread, spread_exact))
    err_imag = max(abs(e.imag) for e in spread_exact)
    err_theta = max(abs(zeros_theta(t) - theta(t)) for t in [10.0, 14.0, 30.0, 100.0] + spread)
    check(
        "D1",
        all(by_terms[k + 1] < by_terms[k] for k in range(6)) and by_terms[6] < 1e-9 and err_all < 1e-9 and err_theta < 1e-9,
        f"the fast formula for Z(t) = exp(i theta(t)) zeta(1/2 + it), which is real on the line (Riemann-Siegel: a main sum of sqrt(t/2pi) terms plus the corrections C0 to C6), "
        f"against zeta summed directly: largest difference {err_all:.0e} "
        f"at 24 heights between 200 and {T:.0f} (the direct sum has an imaginary part of up to {err_imag:.0e} there, which should be 0, so it is no better itself); "
        "at 16 heights between 200 and 400 the largest error after C0, C1, ..., C6 is " + ", ".join(f"{e:.0e}" for e in by_terms)
        + f": each correction lowers it, and with C0 alone the test would fail a million times over; theta from its asymptotic series is within {err_theta:.0e} of core.theta",
    )

    # ---- D2: every correction term is right, not merely helpful
    def scaled(table: list, last: int, n: int) -> float:
        a = n + 0.3  # the same place p = 0.3 between two terms of the main sum, at height 2 pi a^2
        t = 2 * PI * a * a
        return abs(exact(t).real - zeros_make_z(t + 1, table, last, 50.0)(t)) * a ** (last + 1.5)

    ratios = [scaled(zeros_RS_TABLE, k, 6) / scaled(zeros_RS_TABLE, k, 3) for k in range(7)]
    wrong_c4 = [list(row) for row in zeros_RS_TABLE]
    wrong_c4[4][2] = (4, -4, 19, 4096)
    wrong_c5 = [list(row) for row in zeros_RS_TABLE]
    wrong_c5[5][2] = (7, -6, -900, 82575360)
    ratio_c4 = scaled(wrong_c4, 4, 6) / scaled(wrong_c4, 4, 3)
    ratio_c5 = scaled(wrong_c5, 6, 6) / scaled(wrong_c5, 6, 3)
    c0_series = sum(c * (-0.2) ** i for i, c in enumerate(zeros_rs_series(zeros_RS_TABLE)[0]))
    c0_closed = math.cos(2 * PI * (0.3 ** 2 - 0.3 - 1 / 16)) / math.cos(2 * PI * 0.3)
    say("     heights used: " + ", ".join(f"{2 * PI * (n + 0.3) ** 2:.2f}" for n in (3, 6)) + "; error after C_k times a^(k + 3/2), ratio between them: " + ", ".join(f"{r:.3f}" for r in ratios))
    check(
        "D2",
        all(0.8 < r < 1.25 for r in ratios) and ratio_c4 > 1.5 and ratio_c5 > 1.5 and abs(c0_series - c0_closed) < 1e-13,
        "each correction is right, not merely helpful: if C0 to Ck are exact, the error left after Ck, multiplied by a^(k + 3/2) with a = sqrt(t/2pi), is close to the next correction, which depends only on "
        "the position p between two terms of the main sum and not on the height. At p = 0.3 and heights 68.4 and 249.4 (a = 3.3 and 6.3) the two values have ratio "
        + ", ".join(f"{r:.2f}" for r in ratios) + f" for k = 0, ..., 6. Control: a wrong term leaves an error one power of a larger, so the ratio becomes about 6.3/3.3 = 1.9: "
        f"with 19/4096 in place of 19/24576 in C4 it is {ratio_c4:.2f} after C4, and with -900 in place of -901 in one numerator of C5 it is {ratio_c5:.2f} after C6. "
        f"(C0 is the closed form cos(2pi(p^2 - p - 1/16))/cos(2pi p): {c0_closed:.12f} at p = 0.3, {c0_series:.12f} from the series used here)",
    )

    # ---- D3: every zero up to T, and the count by the argument principle
    grid, found, pairs, misses = zeros_find(z, T, H)
    n_grid = len(grid) - 1
    plain = sum(1 for j in range(1, n_grid + 1) if (grid[j - 1] > 0) != (grid[j] > 0))
    s_top, evals_top = zeros_backlund(T)
    n_top = theta(T) / PI + 1 + s_top
    t_mid = 10000.0
    s_mid, _ = zeros_backlund(t_mid)
    n_mid = theta(t_mid) / PI + 1 + s_mid
    found_mid = sum(1 for g in found if g <= t_mid)
    say("     close pairs recovered between grid points: " + ", ".join(f"{a:.4f}/{b:.4f}" for a, b in pairs))
    say("     dips of |Z| on the grid that do not reach zero: " + ", ".join(f"t = {t:.6f}, Z = {v:.6f}" for t, v in misses))
    check(
        "D3",
        len(found) == round(n_top) and abs(n_top - round(n_top)) < 1e-6 and found_mid == round(n_mid) and abs(n_mid - round(n_mid)) < 1e-6
        and len(pairs) > 0 and plain < round(n_top) and len(misses) == 1 and abs(misses[0][0] - 2.4757) < 1e-3,  # 2.4757: regression value
        # the two terms with 1e-6 test only that theta and arg zeta agree with each other: theta/pi + 1 + S is a whole number
        # whatever the zeros are. What tests the zeros is the equality of whole numbers.
        f"zeros of Z with 0 < t <= {T:.0f}: {len(found)} found, {plain} as sign changes between neighbours on a grid of step {H} and {2 * len(pairs)} as {len(pairs)} close pairs "
        f"hiding between grid points, recovered from the dip of |Z| there. The count that needs no zeros, N(T) = theta(T)/pi + 1 + S(T) with S(T) = arg zeta(1/2 + iT)/pi "
        f"followed along the segment from 2 + iT ({evals_top} values of zeta), is {theta(T) / PI + 1:.4f} + ({s_top:+.4f}) = {round(n_top)}, the same number "
        f"(that sum is a whole number whatever the zeros are, so its decimals prove nothing; the match of the two whole numbers is the test); "
        f"at height {t_mid:.0f} the two counts are {found_mid} and {round(n_mid)} (there S = {s_mid:+.4f}, so the smooth part alone would say one too many). "
        f"Control: the sign changes on the grid alone are {round(n_top) - plain} short of N(T). The only dip of |Z| on the grid that does not reach zero is at t = "
        + (f"{misses[0][0]:.4f}, where Z = {misses[0][1]:.4f}" if len(misses) == 1 else f"(found {len(misses)} of them)")
        + ". Both counts are floating-point computations: evidence, not a proof",
    )

    # ---- D4: Turing's average
    window = 100.0
    mean_s = zeros_mean_s(found, T - window, T)
    i_abs = min(range(len(found) - 1), key=lambda i: found[i + 1] - found[i])  # the closest pair in height
    mean_s_cut = zeros_mean_s(found[:i_abs] + found[i_abs + 2:], T - window, T)
    quoted = (1.91 + 0.114 * math.log(T / (2 * PI))) / window
    s_low = min(k - zeros_theta(g) / PI - 1 for k, g in enumerate(found))  # S just below each zero
    s_high = max(k - zeros_theta(g) / PI for k, g in enumerate(found))  # S just above each zero
    check(
        "D4",
        abs(mean_s) < quoted and abs(mean_s_cut + 2) < quoted,  # 1.91 and 0.114: Lehman's constants for Turing's bound (external)
        f"Turing's test that no zero was missed: the average over {T - window:.0f} <= t <= {T:.0f} of [zeros found up to t] - theta(t)/pi - 1 is {mean_s:+.4f}, "
        f"inside the +-{quoted:.3f} that the bound of Turing and Lehman on the integral of S, 1.91 + 0.114 ln(T/2pi), allows (quoted from the literature, not rederived here). "
        f"Zeros can only be missed in pairs, and a pair missed below {T - window:.0f} lowers every later count by two: with the closest pair of zeros struck from the list "
        f"the average is {mean_s_cut:+.4f}, far outside the bound. That is arithmetic, and it is the whole of Turing's argument. "
        f"Over the whole range S stays between {s_low:+.2f} and {s_high:+.2f}. "
        "This is evidence, not a rigorous verification: the values of Z are floating-point numbers without certified error bounds",
    )

    # ---- D5: the zeros are zeros of zeta, located to 2e-9, and they are the published ones
    reach = 2e-9
    bracketed = sum(1 for g in found if (z(g - reach) > 0) != (z(g + reach) > 0))
    shifted = sum(1 for g in found[::50] if (z(g + 2 * reach) > 0) != (z(g + 4 * reach) > 0))
    # external values: these five zeros as tabulated (Odlyzko's tables of zeros), typed in from memory, not read from a file
    published = {1: 14.134725141734694, 10: 49.773832477672302, 100: 236.524229665816206, 1000: 1419.422480945995686, 10000: 9877.782654005501143}
    worst_pub = max(abs(found[i - 1] - g) for i, g in published.items())
    next_door = min(abs(found[i - 1 + shift] - g) for i, g in published.items() for shift in (-1, 1) if i - 1 + shift >= 0)
    stats = zeros_gap_stats(found)
    gaps = stats["gaps"]
    i_norm = min(range(len(gaps)), key=lambda i: gaps[i])  # the closest pair in units of the mean spacing
    sample = sorted({0, 9, 99, 999, 9999, len(found) - 2, i_abs, i_norm})
    at_zero = max(abs(zeta(complex(0.5, found[i + d]))) for i in sample for d in (0, 1))
    between = min(abs(zeta(complex(0.5, 0.5 * (found[i] + found[i + 1])))) for i in sample)
    check(
        "D5",
        bracketed == len(found) and shifted == 0 and worst_pub < 1e-9 and next_door > 0.1 and at_zero < 1e-8 and between > 1e-3,
        f"each of the {len(found)} values is a zero to within {reach:.0e}: Z has opposite signs {reach:.0e} below and above {bracketed} of them (control: between {2 * reach:.0e} and {4 * reach:.0e} "
        f"above every 50th value it changes sign {shifted} times). The 1st, 10th, 100th, 1000th and 10000th ({found[0]:.9f}, {found[9]:.9f}, {found[99]:.9f}, {found[999]:.9f}, {found[9999]:.9f}) "
        f"agree with their tabulated values (typed in from memory) to {worst_pub:.0e}, and the nearest other entry of the list is {next_door:.2f} away, so the numbering is right too. "
        f"Zeta itself, summed directly at {2 * len(sample)} of them (those five and their upper neighbours, the last two, the two closest pairs), is at most {at_zero:.0e} in size; "
        f"control: halfway between the same neighbours |zeta| is at least {between:.4f}",
    )

    # ---- D6: the gaps are neither a lattice nor a gas
    n_gaps = stats["n"]
    noise = 2 / math.sqrt(n_gaps)  # n_gaps independent draws from a law stay this close to it 999 times in 1000 (Kolmogorov)
    bands = [zeros_gap_stats(found[:1001])["var"], zeros_gap_stats([g for g in found if 10000 < g <= 20000])["var"], zeros_gap_stats([g for g in found if g > 20000])["var"]]
    wigner_var, wigner_below, poisson_below = 3 * PI / 8 - 1, zeros_wigner_cdf(0.25), zeros_poisson_cdf(0.25)
    if VERBOSE:
        say("     gap size    zeros   surmise  Poisson   (share of the gaps in each bin)")
        edges = [0.25 * k for k in range(13)]
        for lo, hi in zip(edges, edges[1:]):
            share = sum(1 for x in gaps if lo <= x < hi) / n_gaps
            say(f"     {lo:4.2f}-{hi:4.2f}  {share:7.4f}  {zeros_wigner_cdf(hi) - zeros_wigner_cdf(lo):7.4f}  {zeros_poisson_cdf(hi) - zeros_poisson_cdf(lo):7.4f}")
    check(
        "D6",
        abs(stats["mean"] - 1) < 1e-3 and 0.5 * wigner_var < stats["var"] < wigner_var and 0 < stats["below"] < wigner_below
        and stats["ks_poisson"] > 0.25 and noise < stats["ks_wigner"] < 0.05 and bands[0] < bands[2] < wigner_var,
        f"the {n_gaps} gaps between neighbouring zeros, in units of the local mean spacing (each multiplied by ln(g/2pi)/(2pi)): mean {stats['mean']:.4f}, variance {stats['var']:.3f}, "
        f"{100 * stats['below']:.2f}% of them below 0.25, smallest {stats['min']:.4f}, largest {stats['max']:.2f}. Three references: equal spacing (every gap 1, variance 0), "
        f"independent Poisson points (variance 1, {100 * poisson_below:.1f}% below 0.25), and the Wigner surmise for random Hermitian matrices (variance {wigner_var:.3f}, {100 * wigner_below:.2f}% below 0.25). "
        f"Kolmogorov-Smirnov distance, the largest difference between cumulative distributions: {stats['ks_poisson']:.3f} from Poisson, {stats['ks_wigner']:.3f} from the surmise. "
        f"Neither a lattice nor a gas: close to the surmise, yet measurably more rigid than it ({n_gaps} independent draws from the surmise itself stay within {noise:.3f} of it 999 times in 1000), "
        f"and less so with height: variance {bands[0]:.3f} for the first 1000 gaps, {bands[1]:.3f} between heights 10000 and 20000, {bands[2]:.3f} between 20000 and {T:.0f}",
    )

    # ---- D7: the same statistics on made-up points with the same density as the zeros
    rng = Rng(1859)
    count, counts = 0.5, []
    for _ in range(len(found)):
        counts.append(count)
        count -= math.log(1 - rng.uniform())
    gas = zeros_gap_stats(zeros_heights(counts))
    jitter = 0.1
    lattice = zeros_gap_stats(zeros_heights(sorted(0.5 + k + jitter * rng.gauss() for k in range(len(found)))))
    count, counts = 0.5, []
    for _ in range(len(found)):
        counts.append(count)
        a, d, b_re, b_im = rng.gauss(), rng.gauss(), rng.gauss() / math.sqrt(2), rng.gauss() / math.sqrt(2)  # the matrix [[a, b], [conj b, d]]
        count += math.sqrt((a - d) ** 2 + 4 * (b_re ** 2 + b_im ** 2)) * math.sqrt(PI) / 4  # its eigenvalue gap, scaled to mean 1
    matrix = zeros_gap_stats(zeros_heights(counts))
    check(
        "D7",
        abs(gas["var"] - 1) < 5 * math.sqrt(8 / n_gaps) and abs(gas["below"] - poisson_below) < 5 * math.sqrt(poisson_below * (1 - poisson_below) / n_gaps)
        and gas["ks_poisson"] < noise and gas["ks_wigner"] > 0.25
        and abs(lattice["var"] - 2 * jitter ** 2) < 0.1 * 2 * jitter ** 2 and lattice["below"] == 0 and lattice["ks_poisson"] > 0.25 and lattice["ks_wigner"] > 0.25
        and abs(matrix["var"] - wigner_var) < 5 * 0.26 / math.sqrt(n_gaps) and abs(matrix["below"] - wigner_below) < 5 * math.sqrt(wigner_below * (1 - wigner_below) / n_gaps)
        and matrix["ks_wigner"] < noise and matrix["ks_poisson"] > 0.25,
        f"control for D6: {len(found)} made-up points with the density of the zeros, put through the same code. Independent (Poisson) points: variance {gas['var']:.3f}, "
        f"{100 * gas['below']:.1f}% below 0.25, distance {gas['ks_poisson']:.3f} from Poisson and {gas['ks_wigner']:.3f} from the surmise. A lattice with each point moved at random by about a tenth of a spacing: "
        f"variance {lattice['var']:.4f} (it should be 2 x 0.1^2 = 0.02), smallest gap {lattice['min']:.2f}, distances {lattice['ks_poisson']:.2f} and {lattice['ks_wigner']:.2f}. "
        f"Gaps drawn as the eigenvalue gap of a random 2 by 2 Hermitian matrix, which is what the surmise describes: variance {matrix['var']:.3f}, {100 * matrix['below']:.2f}% below 0.25, "
        f"distance {matrix['ks_wigner']:.3f} from the surmise and {matrix['ks_poisson']:.3f} from Poisson. Each lands on its own reference; the zeros, {stats['ks_wigner']:.3f} from the surmise, land on none exactly",
    )

    # ---- D8: on the line the mean square grows like a logarithm
    euler = sum(1 / n for n in range(1, 1001)) - math.log(1000) - 1 / 2000 + 1 / 12e6 - 1 / 120e12  # Euler's constant
    squares = [v * v for v in grid]
    running, leftover = 0.0, []  # leftover[i] = E(T) = integral of Z^2 over (0, T) - T (ln(T/2pi) + 2 gamma - 1) at T = 2 (i + 1) H
    for j in range(0, n_grid - 1, 2):
        running += (squares[j] + 4 * squares[j + 1] + squares[j + 2]) * H / 3
        t = (j + 2) * H
        leftover.append(running - t * (math.log(t / (2 * PI)) + 2 * euler - 1))
    marks = [100.0, 1000.0, 10000.0, T]
    at_marks = [leftover[int(round(m / (2 * H))) - 1] for m in marks]
    predicted = [math.log(m / (2 * PI)) + 2 * euler - 1 for m in marks]
    mean_left = sum(leftover) / len(leftover)
    size = math.sqrt(sum(e * e / math.sqrt(2 * (i + 1) * H) for i, e in enumerate(leftover)) / len(leftover))  # root mean square of E(T)/T^(1/4)
    worst = max(abs(e) / (2 * (i + 1) * H) ** 0.25 for i, e in enumerate(leftover)) / size
    check(
        "D8",
        abs(euler - 0.5772156649) < 1e-10 and abs(mean_left - PI) < 0.05 and worst < 6
        and all(abs(e / m) < (0.002 if m >= 10000 else 0.02) for m, e in zip(marks, at_marks) if m >= 1000),
        "on the line the mean square does not settle: (1/T) times the integral of |zeta(1/2 + it)|^2 over 0 < t < T, from Z^2 sampled every 0.1, against ln(T/2pi) + 2 gamma - 1 (gamma = "
        f"{euler:.6f}, recomputed from the harmonic sum): " + "; ".join(f"T = {m:.0f}: {e / m + p:.4f} against {p:.4f}" for m, e, p in zip(marks, at_marks, predicted))
        + f". What is left over, E(T) = integral - T (ln(T/2pi) + 2 gamma - 1), swings between {min(leftover):+.0f} and {max(leftover):+.0f}: its typical size is {size:.1f} T^(1/4) "
        f"and it is never more than {worst:.1f} times that. Its average over 0 < T < {T:.0f} is {mean_left:+.3f}: the literature gives it the mean value pi = {PI:.3f}. "
        f"(With ln T in place of ln(T/2pi) it would average {mean_left - math.log(2 * PI) * (T + 2 * H) / 2:+.0f}, by arithmetic: the 2 pi is not optional)",
    )

    # ---- D9, D10: to the right of the line the mean square settles
    t_two = 1000.0
    both = zeros_two_lines(t_two)
    fine, coarse, split = 0.02, 0.2, 2.0  # a fine step near t = 0, where the pole at s = 1 is close
    n_fine, n_coarse = int(round(split / fine)), int(round((t_two - split) / coarse))
    near = [(abs(zeta(0.75)) ** 2, 0.0)] + [both(j * fine) for j in range(1, n_fine + 1)]
    far = [near[-1]] + [both(split + j * coarse) for j in range(1, n_coarse + 1)]
    worst_two = max(abs(v - abs(zeta(complex(sigma, t))) ** 2) / v for t in (0.3, 7.7, 101.3, 999.9) for sigma, v in zip((0.75, 1.0), both(t)))
    zeta_32, zeta_half, zeta_2 = zeta(1.5).real, zeta(0.5).real, zeta(2.0).real
    run_34 = zeros_simpson([v[0] for v in near], fine, 0, n_fine)  # integral of |zeta(3/4 + it)|^2 over 0 < t < 2
    run_1 = zeros_simpson([v[1] for v in near], fine, int(round(1 / fine)), n_fine)  # integral of |zeta(1 + it)|^2 over 1 < t < 2
    heights, over_34, over_1 = [], [], []  # for 10 <= T <= t_two: T, integral - zeta(3/2) T at sigma = 3/4, integral - zeta(2) T at sigma = 1
    for j in range(0, n_coarse - 1, 2):
        run_34 += (far[j][0] + 4 * far[j + 1][0] + far[j + 2][0]) * coarse / 3
        run_1 += (far[j][1] + 4 * far[j + 1][1] + far[j + 2][1]) * coarse / 3
        t = split + (j + 2) * coarse
        if t >= 10:
            heights.append(t)
            over_34.append(run_34 - zeta_32 * t)
            over_1.append(run_1 - zeta_2 * t)
    def fits(scale, values: list[float]) -> list[tuple[float, float]]:
        """The straight-line fit (constant, slope) of values against scale(T), started at T = 10, 30 and 100."""
        out = []
        for start in (10.0, 30.0, 100.0):
            keep = [i for i, t in enumerate(heights) if t >= start]
            out.append(zeros_fit_line([scale(heights[i]) for i in keep], [values[i] for i in keep]))
        return out

    fits_34 = fits(math.sqrt, over_34)
    const_34, root_34 = fits_34[0]
    second, third = 2 * math.sqrt(2 * PI) * zeta_half, -2 * PI * zeta_half  # (2pi)^(2s-1) zeta(2-2s)/(2-2s) at s = 3/4; the constant term

    def two_terms(sigma: float, big_t: float) -> tuple[float, float]:
        return zeta(2 * sigma).real, (2 * PI) ** (2 * sigma - 1) * zeta(2 - 2 * sigma).real * big_t ** (1 - 2 * sigma) / (2 - 2 * sigma)

    merging = [two_terms(sigma, 10000.0) for sigma in (0.5001, 0.500001)]
    log_10000 = math.log(10000.0 / (2 * PI)) + 2 * euler - 1
    check(
        "D9",
        worst_two < 1e-7 and all(abs(c1 - second) < 0.05 and abs(c0 - third) < 0.15 for c0, c1 in fits_34)
        and abs(over_34[-1] - second * math.sqrt(t_two)) < 0.15 * abs(second) * math.sqrt(t_two)
        and abs(sum(merging[0]) - log_10000) < 0.01 and abs(sum(merging[1]) - log_10000) < 1e-4,
        f"to the right of the line the mean square settles, slowly. At sigma = 3/4 the integral of |zeta|^2 over 0 < t < {t_two:.0f} is {run_34:.1f}, a mean of {run_34 / t_two:.4f} against the limit "
        f"zeta(3/2) = {zeta_32:.4f}. Integral minus zeta(3/2) T, fitted over 10 < T < {t_two:.0f} by c1 sqrt(T) + c0: c1 = {root_34:.3f}, c0 = {const_34:+.2f} "
        f"(started at 30 or 100 instead: c1 = {fits_34[1][1]:.3f}, {fits_34[2][1]:.3f}; c0 = {fits_34[1][0]:+.2f}, {fits_34[2][0]:+.2f}: the last digits depend on the window). The second term "
        f"(2pi)^(1/2) zeta(1/2) T^(1/2)/(1/2) has c1 = {second:.3f}, and the literature adds a constant third term -2 pi zeta(1/2) = {third:+.2f}. At T = {t_two:.0f} the first term alone is "
        f"{-over_34[-1]:.1f} above the integral, the two terms together {over_34[-1] - second * math.sqrt(t_two):.1f} below it. As sigma falls to 1/2 the two terms blow up with opposite signs and their sum does not: "
        f"at sigma = 0.5001 and T = 10000 they are {merging[0][0]:+.1f} and {merging[0][1]:+.1f} per unit T, sum {sum(merging[0]):.4f}; at 0.500001 the sum is {sum(merging[1]):.5f}; the logarithm of D8 is {log_10000:.5f}",
    )
    pole = both(0.001)[1]
    fits_1 = fits(math.log, over_1)
    const_1, log_1 = fits_1[0]
    check(
        "D10",
        abs(pole * 1e-6 - 1) < 1e-3 and abs(run_1 / (t_two - 1) - zeta_2) < 0.02 * zeta_2 and all(abs(c1 + PI) < 0.03 for _, c1 in fits_1) and abs(over_1[-1] + PI * math.log(t_two)) < PI * math.log(t_two) / 3,
        f"at sigma = 1 the integral of |zeta(1 + it)|^2 from 0 does not exist: near the pole the integrand is 1/t^2 ({pole:.4g} at t = 0.001). From t = 1 it is {run_1:.1f} over 1 < t < {t_two:.0f}, "
        f"a mean of {run_1 / (t_two - 1):.4f} against zeta(2) = {zeta_2:.4f}. Integral minus zeta(2) T, fitted over 10 < T < {t_two:.0f} by c1 ln T + c0: c1 = {log_1:.3f}, c0 = {const_1:+.2f} "
        f"(started at 30 or 100 instead: c1 = {fits_1[1][1]:.3f}, {fits_1[2][1]:.3f}); the literature's second term is -pi ln T = {-PI:.3f} ln T. At T = {t_two:.0f}, zeta(2) T is {-over_1[-1]:.1f} above the integral and zeta(2) T - pi ln T only {-over_1[-1] - PI * math.log(t_two):.1f} above it. "
        f"(On these two lines |zeta|^2 is summed with t/2 + 20 terms; relative difference from the full sum at most {worst_two:.0e})",
    )

    # ---- D11: equal weight per octave only on the line
    def octave(sigma: float, n: int) -> float:
        return sum(k ** (-2 * sigma) for k in range(n + 1, 2 * n + 1))

    sizes = [10, 100, 10000]
    on_line = [octave(0.5, n) for n in sizes]
    right = [octave(0.75, n) for n in sizes]
    left = [octave(0.25, n) for n in sizes]
    power = {sigma: math.log(octave(sigma, 10000) / octave(sigma, 100)) / math.log(100) for sigma in (0.5, 0.75, 0.25, 0.51)}
    check(
        "D11",
        all(abs(v - math.log(2) + 1 / (4 * n)) < 1 / n ** 2 for v, n in zip(on_line, sizes)) and abs(power[0.5]) < 2e-3 and abs(power[0.75] + 0.5) < 2e-3
        and abs(power[0.25] - 0.5) < 2e-3 and abs(power[0.51]) > 1e-2
        and abs(right[2] * 100 - (2 - math.sqrt(2))) < 1e-3 and abs(left[2] / 100 - 2 * (math.sqrt(2) - 1)) < 1e-3,
        "the weight carried by one octave of integers, the sum of n^(-2 sigma) over N < n <= 2N, for N = 10, 100, 10000. On the line (sigma = 1/2): "
        + ", ".join(f"{v:.5f}" for v in on_line) + f", which is ln 2 - 1/(4N) and tends to ln 2 = {math.log(2):.5f}: in the limit every octave weighs the same. At sigma = 3/4: "
        + ", ".join(f"{v:.5f}" for v in right) + " (0.586/sqrt(N), fading). At sigma = 1/4: " + ", ".join(f"{v:.3f}" for v in left) + " (0.828 sqrt(N), growing). "
        f"Powers of N fitted between 100 and 10000: {power[0.5]:+.4f}, {power[0.75]:+.4f}, {power[0.25]:+.4f} against 0, -1/2, +1/2; control: at sigma = 0.51 the power is already {power[0.51]:+.4f}",
    )

    # ---- D12: the closest pairs, and when they would collide
    pair_abs, pair_norm = (found[i_abs], found[i_abs + 1]), (found[i_norm], found[i_norm + 1])
    gap_abs, gap_norm = pair_abs[1] - pair_abs[0], pair_norm[1] - pair_norm[0]
    tau_abs, tau_norm = -gap_abs ** 2 / 8, -gap_norm ** 2 / 8
    push = sum(1 / ((pair_abs[0] - g) * (pair_abs[1] - g)) for i, g in enumerate(found) if i not in (i_abs, i_abs + 1))
    tau_pushed = math.log(1 - gap_abs ** 2 * push / 2) / (4 * push)
    middle = sorted(found[i + 1] - found[i] for i in range(len(found) - 1))[len(found) // 2]
    check(
        "D12",
        # 7005.0629: the lower zero of Lehmer's pair (external, from memory); 17143.7865: regression value
        0.03 < gaps[i_norm] < 0.05 and abs(pair_norm[0] - 7005.0629) < 1e-3 and abs(pair_abs[0] - 17143.7865) < 1e-3 and gap_abs < gap_norm
        and abs(tau_pushed / tau_abs - 1) < 0.01 and middle ** 2 / 8 > 100 * abs(tau_abs),
        f"the closest pairs among the {len(found)} zeros. In units of the local mean spacing: {pair_norm[0]:.4f} and {pair_norm[1]:.4f} (Lehmer's pair), {gap_norm:.5f} apart, {gaps[i_norm]:.4f} of a mean spacing. "
        f"In height: {pair_abs[0]:.4f} and {pair_abs[1]:.4f}, {gap_abs:.5f} apart ({gaps[i_abs]:.4f} of a mean spacing). Run backward under the de Bruijn-Newman flow, an isolated pair a distance g apart "
        f"collides at tau = -g^2/8: {tau_abs:.3e} for the second pair (the first to collide; {4 * tau_abs:.2e} in the literature's t = 4 tau) and {tau_norm:.3e} for Lehmer's ({4 * tau_norm:.2e}). "
        f"Letting all the other zeros found push on the pair from where they stand moves the first figure only to {tau_pushed:.3e}. These are estimates from two zeros, not bounds on the constant; "
        f"control: a pair at the median distance ({middle:.3f}) would give {-middle ** 2 / 8:.3f}, {middle ** 2 / gap_abs ** 2:.0f} times further back",
    )


def section_zeros() -> None:
    """The checks of zeros_run. Most of them build on the list of zeros found in D3, so a failure there can make
    a later step raise; the checks not yet reported are then failed, and the program goes on."""
    start = len(RESULTS)
    try:
        zeros_run()
    except Exception as err:
        for name in zeros_NAMES[len(RESULTS) - start:]:
            check(name, False, f"not computed: an earlier step raised {type(err).__name__} ({err})")


# ====================================================================================================
# section E: mirror

TITLE_MIRROR = "E. The mirror is not enough: a function with zeta's symmetry and zeros off the line"

mirror_KAPPA = (math.sqrt(10 - 2 * math.sqrt(5)) - 2) / (math.sqrt(5) - 1)


def mirror_dh(s: complex, kappa: float = mirror_KAPPA) -> complex:
    """Davenport and Heilbronn's function: the Dirichlet series whose coefficients repeat
    1, kappa, -kappa, -1, 0 with period five, continued to the plane through Hurwitz zeta."""
    s = complex(s)
    return cmath.exp(-s * math.log(5)) * (hurwitz(s, 0.2) + kappa * hurwitz(s, 0.4) - kappa * hurwitz(s, 0.6) - hurwitz(s, 0.8))


def mirror_factor(s: complex) -> complex:
    """The factor X(s) in f(s) = X(s) f(1 - s); it has modulus one on the critical line."""
    s = complex(s)
    return cmath.exp((0.5 - s) * math.log(5) + (s - 1) * math.log(2 * PI) + loggamma(1 - s)) * 2 * cmath.cos(PI * s / 2)


def mirror_theta(t: float) -> float:
    return loggamma(0.75 + 0.5j * t).imag + 0.5 * t * math.log(5 / PI)


def mirror_zf(t: float) -> complex:
    """exp(i theta_f(t)) f(1/2 + it): real for real t, as Z(t) is for zeta."""
    return cmath.exp(1j * mirror_theta(t)) * mirror_dh(0.5 + 1j * t)


def mirror_z(t: float) -> float:
    return (cmath.exp(1j * theta(t)) * zeta(0.5 + 1j * t)).real


def mirror_newton(f, s: complex, steps: int = 12, h: float = 1e-6) -> complex:
    for _ in range(steps):
        d = (f(s + h) - f(s - h)) / (2 * h)
        s = s - f(s) / d
    return s


def mirror_sign_changes(f, a: float, b: float, step: float) -> list[float]:
    out = []
    n = int(round((b - a) / step))
    prev = f(a)
    for j in range(n):
        lo, hi = a + j * step, a + (j + 1) * step
        cur = f(hi)
        if (prev > 0) != (cur > 0):
            out.append(bisect(f, lo, hi, 1e-10))
        prev = cur
    return out


def mirror_box(lo: float, hi: float, bottom: float, top: float) -> list[complex]:
    """The rectangle lo < Re s < hi, bottom < Im s < top, counter-clockwise, its long sides cut into
    pieces at most one unit long so that the sampling of the boundary does not thin out with height."""
    steps = max(1, int(math.ceil(top - bottom)))
    up = [complex(hi, bottom + (top - bottom) * j / steps) for j in range(steps + 1)]
    down = [complex(lo, top - (top - bottom) * j / steps) for j in range(steps + 1)]
    return up + down


def mirror_count(f, lo: float, hi: float, bottom: float, top: float) -> int:
    """Zeros of f in the box, by winding number, 32 sample points to every unit of boundary to start with."""
    return winding(f, mirror_box(lo, hi, bottom, top), pieces=32)


def mirror_polya(x: complex, h: float = 0.01, u_max: float = 1.6) -> complex:
    """Polya's function: the Fourier transform of one bump's leading part, made even by hand:
    integral of 2 pi^2 (e^(9u/2) + e^(-9u/2)) exp(-pi (e^(2u) + e^(-2u))) e^(ixu) du."""
    total = 0.5 * 4 * PI ** 2 * math.exp(-2 * PI)
    k = int(round(u_max / h))
    for j in range(1, k + 1):
        u = j * h
        total += 4 * PI ** 2 * math.cosh(4.5 * u) * math.exp(-2 * PI * math.cosh(2 * u)) * cmath.cos(x * u)
    return 2 * h * total


def section_mirror() -> None:
    kappa = mirror_KAPPA

    # E1: the series, the mirror, and the one value of kappa that has it
    coeffs = [0.0, 1.0, kappa, -kappa, -1.0]
    s0 = 3 + 2j
    series = sum(coeffs[n % 5] * cmath.exp(-s0 * math.log(n)) for n in range(1, 60000))
    gap_series = abs(series - mirror_dh(s0))
    points = (0.3 + 4j, 0.7 + 20j, -1.5 + 3j, 2.5 - 7j, 0.5 + 85j, 0.1 + 50j, 1.2 + 0.3j, 0.25 + 0.1j)
    worst = max(abs(mirror_dh(s) - mirror_factor(s) * mirror_dh(1 - s)) / abs(mirror_dh(s)) for s in points)
    wrong = min(abs(mirror_dh(s, 0.3) - mirror_factor(s) * mirror_dh(1 - s, 0.3)) / abs(mirror_dh(s, 0.3)) for s in points[:4])
    # solve the mirror equation for kappa at each point: it is linear in kappa
    solved = []
    for s in points:
        e, e1 = cmath.exp(-s * math.log(5)), cmath.exp(-(1 - s) * math.log(5))
        p, q = e * (hurwitz(s, 0.2) - hurwitz(s, 0.8)), e * (hurwitz(s, 0.4) - hurwitz(s, 0.6))
        p1, q1 = e1 * (hurwitz(1 - s, 0.2) - hurwitz(1 - s, 0.8)), e1 * (hurwitz(1 - s, 0.4) - hurwitz(1 - s, 0.6))
        x = mirror_factor(s)
        solved.append(-(p - x * p1) / (q - x * q1))
    spread = max(abs(k - kappa) for k in solved)
    on_line = max(abs(abs(mirror_factor(0.5 + 1j * t)) - 1) for t in (1.0, 5.0, 20.0, 85.0))
    check(
        "E1",
        gap_series < 1e-9 and worst < 1e-10 and wrong > 0.005 and spread < 1e-9 and on_line < 1e-12,
        f"Davenport and Heilbronn's function f(s) = 1 + k/2^s - k/3^s - 1/4^s + 0/5^s + 1/6^s + ..., coefficients repeating with period five, k = {kappa:.10f} "
        f"(the series at 3 + 2i is within {gap_series:.0e} of the continued function). It has zeta's kind of mirror: f(s) = X(s) f(1 - s) with "
        f"X(s) = 5^(1/2 - s) 2 (2 pi)^(s - 1) Gamma(1 - s) cos(pi s/2), to {worst:.0e} at eight points, and |X| = 1 on the line Re s = 1/2 (to {tiny(on_line)}). "
        f"Control: with k = 0.3 the mirror fails by at least {wrong:.3f}; solving the mirror equation for k at each of the eight points gives the same k to {spread:.0e}",
    )

    # E2: on the line f is real up to a phase, and most zeros are there
    imag = max(abs(mirror_zf(t).imag) for t in (0.0, 1.0, 5.0, 20.0, 85.0, 85.7))
    line_zeros = mirror_sign_changes(lambda t: mirror_zf(t).real, 0.0, 116.0, 0.05)
    line_below_100 = [t for t in line_zeros if t < 100]
    finer = mirror_sign_changes(lambda t: mirror_zf(t).real, 0.0, 100.0, 0.02)
    zeta_line = mirror_sign_changes(mirror_z, 1.0, 100.0, 0.05)
    smallest_gap = min(b - a for a, b in zip(line_below_100, line_below_100[1:]))
    check(
        "E2",
        imag < 1e-11 and len(line_below_100) == len(finer) and smallest_gap > 0.2 and len(zeta_line) == 29
        and abs(line_zeros[0] - 5.094160) < 1e-5,  # 29: the known count of zeta's zeros below 100 (external); 5.094160: regression value
        f"on the line, exp(i theta_f(t)) f(1/2 + it) is real (largest imaginary part {imag:.0e}), so its zeros there show as sign changes: {len(line_below_100)} of them "
        f"for 0 < t < 100, the first at {line_zeros[0]:.6f} (the same number on a grid of 0.05 and of 0.02; the closest two are {smallest_gap:.2f} apart). "
        f"Zeta has {len(zeta_line)} in the same range, counted the same way",
    )

    # E3: and some zeros are not on the line
    rho = mirror_newton(mirror_dh, 0.808517 + 85.699348j)  # starting values: Spira's list (external)
    mirror_image = 1 - rho.conjugate()
    size_rho, size_mirror = abs(mirror_dh(rho)), abs(mirror_dh(mirror_image))
    size_line = abs(mirror_dh(0.5 + 1j * rho.imag))
    wind_rho = mirror_count(mirror_dh, rho.real - 0.05, rho.real + 0.05, rho.imag - 0.05, rho.imag + 0.05)
    wind_mirror = mirror_count(mirror_dh, mirror_image.real - 0.05, mirror_image.real + 0.05, rho.imag - 0.05, rho.imag + 0.05)
    rho2 = mirror_newton(mirror_dh, 0.650830 + 114.163343j)
    size_rho2 = abs(mirror_dh(rho2))
    wind_rho2 = mirror_count(mirror_dh, rho2.real - 0.05, rho2.real + 0.05, rho2.imag - 0.05, rho2.imag + 0.05)
    check(
        "E3",
        size_rho < 1e-12 and size_mirror < 1e-10 and size_line > 0.3 and wind_rho == 1 and wind_mirror == 1
        and (f"{rho.real:.6f}", f"{rho.imag:.6f}", f"{rho2.real:.6f}", f"{rho2.imag:.6f}") == ("0.808517", "85.699348", "0.650830", "114.163343")
        and size_rho2 < 1e-12 and wind_rho2 == 1,  # the four strings: Spira's published values (external)
        f"f has a zero at {rho.real:.10f} + {rho.imag:.10f}i, well off the line: |f| there is {tiny(size_rho)}, against {size_line:.3f} on the line at the same height, "
        f"and the argument of f winds once round a small square about it. The mirror sends it to a second zero at {mirror_image.real:.10f} + {mirror_image.imag:.10f}i "
        f"(|f| = {size_mirror:.0e}, winding {wind_mirror}). Another such pair is at {rho2.real:.6f} + {rho2.imag:.6f}i and its image (|f| = {size_rho2:.0e}, winding {wind_rho2}). "
        "Both agree with the values Spira published in 1994 to the six decimals he gave",
    )

    # E4: count everything in the strip, both ways, for f and for zeta
    def on_line(a: float, b: float) -> int:
        return sum(1 for t in line_zeros if a < t < b)

    spans = [(0.5, 80.0), (80.0, 90.0), (90.0, 113.5), (113.5, 116.0)]
    by_winding = [mirror_count(mirror_dh, 0.0, 1.0, a, b) for a, b in spans]
    by_sign = [on_line(a, b) for a, b in spans]
    wide = mirror_count(mirror_dh, -1.0, 2.0, 80.0, 90.0)
    lowest = mirror_count(mirror_dh, -0.03, 1.03, -0.5, 0.5)  # the bottom of the strip, across the real axis
    all_zeta = mirror_count(zeta, 0.0, 1.0, 80.0, 90.0)
    line_zeta = [t for t in zeta_line if 80 < t < 90]
    check(
        "E4",
        by_winding[0] == by_sign[0] and by_winding[1] == by_sign[1] + 2 and by_winding[2] == by_sign[2] and by_winding[3] == by_sign[3] + 2
        and by_sign[3] == 0 and wide == by_winding[1] and lowest == 0 and all_zeta == 4 and len(line_zeta) == 4,
        "every zero of f in the strip 0 < Re s < 1 up to height 116, counted by winding number and, on the line, by sign changes. "
        + f"Below height 0.5: {lowest}, from a box across the real axis; "
        + "; ".join(f"heights {a:g} to {b:g}: {w} in the strip, {c} on the line" for (a, b), w, c in zip(spans, by_winding, by_sign))
        + f". So the pair near height 85.7 is the first off the line and the pair near 114.2 the second, and everything else below 116 is on it "
        f"(a wider box, -1 < Re s < 2, between 80 and 90 holds {wide} too). Control: zeta between 80 and 90 has {all_zeta} by winding and {len(line_zeta)} on the line. "
        "The same count on the same box tells the two functions apart",
    )

    # E5: what f lacks is the product over primes
    a = {n: coeffs[n % 5] for n in range(1, 10)}
    not_mult = a[2] * a[3] - a[6]
    # zeta's coefficients are all 1, trivially multiplicative; a Dirichlet character's are too
    chi5 = [0, 1, 1j, -1j, -1]
    char_mult = max(abs(chi5[m % 5] * chi5[n % 5] - chi5[(m * n) % 5]) for m in range(1, 30) for n in range(1, 30))
    half = (1 - 1j * kappa) / 2
    as_sum = max(abs(half * chi5[n % 5] + half.conjugate() * chi5[n % 5].conjugate() - coeffs[n % 5]) for n in range(5)) if True else 0.0
    check(
        "E5",
        abs(not_mult) > 0.5 and char_mult < 1e-12 and as_sum < 1e-12,
        f"what f lacks: its coefficients do not multiply. a(2) a(3) = {a[2] * a[3]:+.4f} but a(6) = {a[6]:+.0f}, so f is no product over primes. "
        f"It is a sum of two functions that are: f = c L(s, chi) + conj(c) L(s, conj chi) with chi the character mod 5 sending 2 to i and c = (1 - ik)/2 "
        f"(coefficients agree to {tiny(as_sum)}; chi itself multiplies, worst gap {tiny(char_mult)}). Two products added are not a product",
    )

    # E6: one bump made even by hand has only real zeros (Polya)
    real_zeros = mirror_sign_changes(lambda x: mirror_polya(x).real, 0.5, 40.0, 0.05)
    polya_box = [complex(0.5 + 39.5 * j / 40, -1.5) for j in range(41)] + [complex(40.0 - 39.5 * j / 40, 1.5) for j in range(41)]
    polya_all = winding(mirror_polya, polya_box, pieces=16)
    xi_zeros = mirror_sign_changes(lambda x: xi_from_phi(x), 0.5, 40.0, 0.05)
    check(
        "E6",
        len(real_zeros) == polya_all and len(real_zeros) >= 5 and len(xi_zeros) == 6,
        f"Polya's function, the transform of one bump's leading part made even by hand, 2 pi^2 (e^(9u/2) + e^(-9u/2)) exp(-pi (e^(2u) + e^(-2u))): "
        f"{len(real_zeros)} real zeros between 0.5 and 40 (the first at {real_zeros[0]:.4f}, the last at {real_zeros[-1]:.4f}) and {polya_all} zeros of any kind "
        f"in the box |Im x| < 1.5 round them, so none off the axis there; Polya proved in 1926 that it has none anywhere. Xi itself has {len(xi_zeros)} real zeros "
        f"in the same range, the first at {xi_zeros[0]:.4f}",
    )

    # E7: where else the mirror factor of zeta has modulus one
    on = max(abs(abs(chi(0.5 + 1j * t)) - 1) for t in (3.0, 14.0, 50.0, 200.0))
    cross = bisect(lambda t: abs(chi(0.3 + 1j * t)) - 1, 3.0, 12.0)
    cross2 = bisect(lambda t: abs(chi(0.9 + 1j * t)) - 1, 3.0, 12.0)
    far = abs(chi(0.3 + 100j))
    predicted = (100 / (2 * PI)) ** 0.2
    check(
        "E7",
        on < 1e-12 and abs(cross - 6.29) < 0.01 and abs(far / predicted - 1) < 0.01 and 6.0 < cross2 < 6.6,
        f"zeta's own mirror factor chi(s), in zeta(s) = chi(s) zeta(1 - s), has modulus one on the critical line (to {tiny(on)} at four heights) "
        f"and also along a curve that crosses the strip near height 2 pi: at Re s = 0.3 it is at t = {cross:.4f}, at Re s = 0.9 at t = {cross2:.4f}. "
        f"Higher up the line is the only place: |chi(0.3 + 100i)| = {far:.4f}, which is (t/2pi)^(1/2 - 0.3) = {predicted:.4f}",
    )


# ====================================================================================================
# section F: lattice

TITLE_LATTICE = "F. Two lattices that are their own mirror image: the Ising magnet in temperature, and percolation"


# ---- the Ising model on small graphs


def lattice_grid_and_dual(rows: int, cols: int) -> tuple[int, list[tuple[int, int]], int, list[tuple[int, int]]]:
    """A rows x cols grid of points with its nearest-neighbour bonds, and its planar dual:
    one point per square face plus one for the outside, one dual bond across every bond."""
    def at(r: int, c: int) -> int:
        return r * cols + c

    def face(r: int, c: int) -> int:
        """the square whose lower-left corner is (r, c); the outside is the last index"""
        if 0 <= r < rows - 1 and 0 <= c < cols - 1:
            return r * (cols - 1) + c
        return (rows - 1) * (cols - 1)

    bonds, dual = [], []
    for r in range(rows):
        for c in range(cols):
            if c + 1 < cols:  # horizontal bond: the faces above and below it
                bonds.append((at(r, c), at(r, c + 1)))
                dual.append((face(r - 1, c), face(r, c)))
            if r + 1 < rows:  # vertical bond: the faces left and right of it
                bonds.append((at(r, c), at(r + 1, c)))
                dual.append((face(r, c - 1), face(r, c)))
    return rows * cols, bonds, (rows - 1) * (cols - 1) + 1, dual


def lattice_partition(points: int, bonds: list[tuple[int, int]], k: float) -> float:
    """sum over all spin configurations of exp(k * sum over bonds of s_i s_j)"""
    total = 0.0
    for mask in range(1 << points):
        e = 0
        for a, b in bonds:
            e += 1 if ((mask >> a) ^ (mask >> b)) & 1 == 0 else -1
        total += math.exp(k * e)
    return total


def lattice_cylinder_counts(rows: int, cols: int) -> dict[tuple[int, int, int, int], int]:
    """Every configuration of a rows x cols lattice wrapped round a cylinder, sorted by
    (sum over horizontal bonds, sum over vertical bonds inside, sum of the top row,
    sum of the bottom row with alternating signs): how many configurations have each."""
    counts: dict[tuple[int, int, int, int], int] = {}
    for mask in range(1 << (rows * cols)):
        s = [1 - 2 * ((mask >> q) & 1) for q in range(rows * cols)]
        eh = ev = 0
        for r in range(rows):
            base = r * cols
            for c in range(cols):
                eh += s[base + c] * s[base + (c + 1) % cols]
                if r + 1 < rows:
                    ev += s[base + c] * s[base + cols + c]
        top = sum(s[c] for c in range(cols))
        bottom = sum(s[(rows - 1) * cols + c] * (1 if c % 2 == 0 else -1) for c in range(cols))
        key = (eh, ev, top, bottom)
        counts[key] = counts.get(key, 0) + 1
    return counts


def lattice_energy_table(counts: dict[tuple[int, int, int, int], int], weights: tuple[int, int, int, int]) -> dict[int, int]:
    table: dict[int, int] = {}
    for key, n in counts.items():
        e = sum(w * x for w, x in zip(weights, key))
        table[e] = table.get(e, 0) + n
    return table


def lattice_zero_temperatures(table: dict[int, int]) -> tuple[list[complex], int]:
    """All complex K (one representative each) at which sum n_e exp(K e) vanishes, as
    (the zeros away from x = -1, how many times x = -1 is a zero), where x = exp(step K) is
    the variable the sum is a polynomial in. The zero at x = -1 is
    divided out exactly first (the coefficients are whole numbers): it can be a multiple zero,
    which the root finder is poor at."""
    lowest = min(table)
    step = 0
    for e in table:
        step = math.gcd(step, e - lowest)
    coeffs = [0] * ((max(table) - lowest) // step + 1)
    for e, n in table.items():
        coeffs[(e - lowest) // step] = n
    trivial = 0
    while sum(c * (-1) ** k for k, c in enumerate(coeffs)) == 0:  # divide by (x + 1), exactly
        quotient = [0] * (len(coeffs) - 1)
        carry = 0
        for k in range(len(coeffs) - 1, 0, -1):
            carry = coeffs[k] - carry
            quotient[k - 1] = carry
        coeffs = quotient
        trivial += 1
    roots = poly_roots([float(c) for c in coeffs])
    return [cmath.log(x) / step for x in roots], trivial


def lattice_at(table: dict[int, int], k: complex) -> complex:
    return sum(n * cmath.exp(k * e) for e, n in table.items())


def lattice_relative(table: dict[int, int], k: complex) -> float:
    """|sum| at K over the sum of the sizes of its terms: 0 at a zero (infinite if K is not a number)."""
    size = sum(n * abs(cmath.exp(k * e)) for e, n in table.items())
    value = abs(lattice_at(table, k)) / size if size > 0 else math.inf
    return value if value == value else math.inf


def lattice_two_dials(counts: dict[tuple[int, int, int, int], int], k_across: float, k_up: float) -> float:
    """The partition function with Brascamp and Kunz's boundary and separate couplings: k_across on the
    horizontal bonds, k_up on the vertical ones (the bonds to the two boundary rows are vertical)."""
    return sum(n * math.exp(k_across * eh + k_up * (ev + top + bottom)) for (eh, ev, top, bottom), n in counts.items())


def lattice_product(rows: int, cols: int, k: complex) -> complex:
    """Brascamp and Kunz: 2^(rows cols) times the product of 1 + z^2 - z (cos a_i + cos b_j), z = sinh 2K."""
    z = cmath.sinh(2 * k)
    prod = complex(2 ** (rows * cols))
    for i in range(1, cols // 2 + 1):
        for j in range(1, rows + 1):
            prod *= 1 + z * z - z * (math.cos((2 * i - 1) * PI / cols) + math.cos(j * PI / (rows + 1)))
    return prod


# ---- percolation on the rectangle that is its own dual


def lattice_edges(n: int) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Bonds of the rectangle with n + 1 columns and n rows of points, without the bonds lying
    in its left and right sides, and for each the dual bond that crosses it. Points are numbered
    column * n + row; dual points (n columns, n + 1 rows) column * (n + 1) + row."""
    primal, dual = [], []
    for i in range(n):
        for j in range(n):  # horizontal bond from (i, j) to (i + 1, j); crossed by a vertical dual bond
            primal.append((i * n + j, (i + 1) * n + j))
            dual.append((i * (n + 1) + j, i * (n + 1) + j + 1))
    for i in range(1, n):
        for j in range(n - 1):  # vertical bond from (i, j) to (i, j + 1); crossed by a horizontal dual bond
            primal.append((i * n + j, i * n + j + 1))
            dual.append(((i - 1) * (n + 1) + j + 1, i * (n + 1) + j + 1))
    return primal, dual


def lattice_joined(points: int, bonds: list[tuple[int, int]], use: list[bool], starts: list[int], ends: list[int]) -> bool:
    """Is some point of `starts` joined to some point of `ends` through the bonds marked in `use`?"""
    parent = list(range(points + 2))
    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for s in starts:
        parent[find(s)] = find(points)
    for t in ends:
        parent[find(t)] = find(points + 1)
    for (a, b), on in zip(bonds, use):
        if on:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
    return find(points) == find(points + 1)


def lattice_crossings(n: int, is_open: list[bool], primal, dual) -> tuple[bool, bool]:
    """(open bonds join left to right, dual bonds across closed bonds join bottom to top)"""
    left = [j for j in range(n)]
    right = [n * n + j for j in range(n)]
    bottom = [i * (n + 1) for i in range(n)]
    top = [i * (n + 1) + n for i in range(n)]
    across = lattice_joined((n + 1) * n, primal, is_open, left, right)
    blocked = lattice_joined(n * (n + 1), dual, [not o for o in is_open], bottom, top)
    return across, blocked


def section_lattice() -> None:
    # F1: Kramers and Wannier: a planar magnet at K and its dual magnet at K*, sinh 2K sinh 2K* = 1
    points, bonds, faces, dual_bonds = lattice_grid_and_dual(3, 3)
    worst, wrong = 0.0, float("inf")
    rows = []
    k_c = 0.5 * math.log(1 + math.sqrt(2))
    for k in (0.2, k_c, 0.8):
        k_dual = -0.5 * math.log(math.tanh(k))
        lhs = lattice_partition(points, bonds, k) / (2 ** points * math.cosh(k) ** len(bonds))
        rhs = lattice_partition(faces, dual_bonds, k_dual) / (2 * math.exp(k_dual * len(bonds)))
        worst = max(worst, abs(lhs / rhs - 1))
        if k != k_c:  # control: the dual magnet at the same temperature instead of the dual one
            same = lattice_partition(faces, dual_bonds, k) / (2 * math.exp(k * len(bonds)))
            wrong = min(wrong, abs(lhs / same - 1))
        rows.append(f"K = {k:.4f}, K* = {k_dual:.4f}: {lhs:.10f} and {rhs:.10f}")
    check(
        "F1",
        worst < 1e-12 and wrong > 0.3 and len(bonds) == 12 and faces == 5 and abs(math.sinh(2 * k_c) - 1) < 1e-12,
        "Kramers and Wannier's duality, exact on a finite planar magnet: for the 3 by 3 grid (9 spins, 12 bonds) and its dual (5 spins, one for each square "
        "and one for the outside, the same 12 bonds crossed), Z(K) / (2^9 cosh^12 K) = Z*(K*) / (2 e^(12 K*)) whenever sinh 2K sinh 2K* = 1, both sides summed "
        f"over every configuration: {'; '.join(rows)} (largest relative gap {worst:.0e}). Control: with the dual magnet taken at K instead of K*, the two sides differ "
        f"by at least {wrong:.2f} of themselves at the first and third temperatures. Hot on one side is cold on the other, and the one temperature that is its own image is sinh 2K = 1, "
        f"K = {k_c:.6f}",
    )

    # F2: the zeros of the partition function in complex temperature, three versions of one lattice
    rows_n, cols_n = 2, 6
    counts = lattice_cylinder_counts(rows_n, cols_n)
    special = lattice_energy_table(counts, (1, 1, 1, 1))   # a row of + above, a row of + - + - below
    free = lattice_energy_table(counts, (1, 1, 0, 0))      # nothing above or below
    lopsided = lattice_energy_table(counts, (1, 2, 2, 2))  # the special one with every vertical bond twice as strong
    zeros_special, trivial_special = lattice_zero_temperatures(special)
    off_special = max(abs(abs(cmath.sinh(2 * k)) - 1) for k in zeros_special)
    zeros_free, trivial_free = lattice_zero_temperatures(free)
    radii_free = sorted(abs(cmath.sinh(2 * k)) for k in zeros_free)
    zeros_lop, trivial_lop = lattice_zero_temperatures(lopsided)
    radii_lop = sorted(abs(cmath.sinh(2 * k) * cmath.sinh(4 * k)) for k in zeros_lop)
    # every value returned is put back into the sum over configurations it came from
    residual = max([lattice_relative(special, k) for k in zeros_special] + [lattice_relative(free, k) for k in zeros_free]
                   + [lattice_relative(lopsided, k) for k in zeros_lop])
    formula_gap = 0.0
    for size in ((2, 6), (2, 4), (3, 4), (1, 4)):
        table = special if size == (2, 6) else lattice_energy_table(lattice_cylinder_counts(*size), (1, 1, 1, 1))
        for k in (0.2, 0.4407, 0.7, 0.3 + 0.4j):
            formula_gap = max(formula_gap, abs(lattice_at(table, k) / lattice_product(size[0], size[1], k) - 1))
    # is the finite lattice its own mirror image?  Z(K*) (sinh 2K)^(MN) / Z(K) is 1 if it is
    def dual(k: float) -> float:
        return -0.5 * math.log(math.tanh(k))

    mirror_special, mirror_free = [], []
    for k in (0.2, 0.3, 0.5, 0.7):
        factor = math.sinh(2 * k) ** (rows_n * cols_n)
        mirror_special.append((lattice_at(special, dual(k)) * factor / lattice_at(special, k)).real)
        mirror_free.append((lattice_at(free, dual(k)) * factor / lattice_at(free, k)).real)
    # with unequal bonds the mirror also swaps the two directions: (across, up) goes to (dual of up, dual of across)
    mirror_swap = []
    for k_across, k_up in ((0.2, 0.4), (0.3, 0.6), (0.5, 1.0), (0.25, 0.7)):
        factor = (math.sinh(2 * k_across) * math.sinh(2 * k_up)) ** (rows_n * cols_n // 2)
        mirror_swap.append(lattice_two_dials(counts, dual(k_up), dual(k_across)) * factor / lattice_two_dials(counts, k_across, k_up))
    no_swap = lattice_two_dials(counts, dual(0.2), dual(0.4)) * (math.sinh(0.4) * math.sinh(0.8)) ** 6 / lattice_two_dials(counts, 0.2, 0.4)  # control: the mirror without the swap
    dual_ratio = dual(0.2) / dual(0.4)  # the image of (0.2, 0.4) is (dual(0.4), dual(0.2)): up over across
    distinct_free = sorted({round(r, 3) for r in radii_free})
    distinct_lop = sorted({round(r, 3) for r in radii_lop})
    check(
        "F2",
        len(zeros_special) == 12 and trivial_special == 0 and off_special < 1e-8
        and len(zeros_free) == 12 and trivial_free == 6 and min(abs(r - 1) for r in radii_free) > 0.02
        and len(zeros_lop) == 16 and trivial_lop == 2 and min(abs(r - 1) for r in radii_lop) > 0.1
        and residual < 1e-9 and formula_gap < 1e-11
        and max(abs(v - 1) for v in mirror_special) < 1e-10 and min(abs(v - 1) for v in mirror_free) > 0.05
        and max(abs(v - 1) for v in mirror_swap) < 1e-10 and abs(no_swap - 1) > 0.05 and abs(dual_ratio - 2) > 0.1,
        f"the zeros of an Ising magnet's partition function in complex temperature (Fisher's zeros), for a 2 by 6 lattice wrapped round a cylinder, all 4096 configurations summed. "
        f"With Brascamp and Kunz's boundary (a row of + above, a row of + - + - below) the finite lattice is exactly its own mirror image, "
        f"Z(K*) (sinh 2K)^12 = Z(K) (the ratio is 1 to {tiny(max(abs(v - 1) for v in mirror_special))} at four temperatures), and all {len(zeros_special)} zeros lie on the circle "
        f"|sinh 2K| = 1, the fixed set of the duality (furthest from it: {tiny(off_special)}). Two controls. Free above and below, the finite lattice has lost its mirror: "
        f"the same ratio is " + ", ".join(f"{v:.2f}" for v in mirror_free) + f", not 1, and at {len(zeros_free)} zeros |sinh 2K| is "
        + ", ".join(f"{r:.3f}" for r in distinct_free)
        + f", near the circle and not on it (the other {trivial_free} are the zero of cosh K, {trivial_free} times over). With the vertical bonds twice as strong the lattice keeps "
        f"an exact mirror, but one that also swaps the two directions: with couplings (a, b) sent to (b*, a*) the ratio is 1 to {tiny(max(abs(v - 1) for v in mirror_swap))} at four "
        f"pairs of couplings (without the swap it is {no_swap:.2f}). That mirror sends (0.2, 0.4) to a pair in the ratio {dual_ratio:.2f}, not 2, so it does not map the one dial K to itself, "
        f"and on |sinh 2K sinh 4K| = 1, where it would fix the dial, the product at {len(zeros_lop)} of the {len(zeros_lop) + trivial_lop} zeros is "
        + ", ".join(f"{r:.3f}" for r in distinct_lop)
        + f", and at the other {trivial_lop} it is 0. Every value found is a zero of the sum it came from (relative size {tiny(residual)}). "
        f"Brascamp and Kunz's product formula, 2^(MN) times the product of 1 + z^2 - z (cos a_i + cos b_j) with z = sinh 2K, agrees with the sum over configurations on four sizes "
        f"at four temperatures to {tiny(formula_gap)}",
    )

    # F3: the zeros close on the transition point only as the lattice grows
    def nearest_zero(side: int) -> float:
        """Distance from z = sinh 2K = 1 of the nearest zero of the product formula, lattice of side - 1 rows by side columns."""
        best = PI
        for i in range(1, side // 2 + 1):
            for j in range(1, side):
                c = 0.5 * (math.cos((2 * i - 1) * PI / side) + math.cos(j * PI / side))
                best = min(best, math.acos(max(-1.0, min(1.0, c))))
        return 2 * math.sin(best / 2)

    gaps = [(side, nearest_zero(side)) for side in (4, 8, 16, 64, 256)]
    # and the sum over configurations does vanish there, for the one size small enough to sum: 3 rows by 4 columns
    table34 = lattice_energy_table(lattice_cylinder_counts(3, 4), (1, 1, 1, 1))
    at_zero = lattice_relative(table34, 0.5 * cmath.asinh(cmath.exp(1j * PI / 4)))
    beside = lattice_relative(table34, 0.5 * cmath.asinh(1.05 * cmath.exp(1j * PI / 4)))
    real_min = min(lattice_at(special, 0.01 * q).real for q in range(1, 200))
    check(
        "F3",
        abs(gaps[0][1] - 2 * math.sin(PI / 8)) < 1e-12 and at_zero < 1e-12 and beside > 1e-4
        and all(b[1] < a[1] for a, b in zip(gaps, gaps[1:])) and all(abs(gap * side / PI - 1) < (0.03 if side < 64 else 0.001) for side, gap in gaps),
        "the transition is where the circle of zeros closes on the real axis, at sinh 2K = 1, and it closes only in the limit. With Brascamp and Kunz's boundary on a lattice of "
        "N - 1 rows by N columns, the zero nearest sinh 2K = 1, found by going through the factors of their product, is at distance "
        + ", ".join(f"{gap:.5f}" for _, gap in gaps) + " for N = " + ", ".join(str(side) for side, _ in gaps)
        + f": close to pi/N and never zero. For N = 4 the sum over all 4096 configurations does vanish at that point (it is {tiny(at_zero)} of the size of its terms; "
        f"control, 5% further from the origin, {beside:.1e}). On the real axis every term of the sum is positive, so nothing can vanish at a real temperature "
        f"(least value of the 2 by 6 sum on 0 < K < 2: {real_min:.1f})",
    )

    # F4: percolation: one of two crossings always happens, and at one half the odds are even at every size
    rows = []
    ok = True
    both_total = neither_total = 0
    for n in (1, 2, 3):
        primal, dual = lattice_edges(n)
        m = len(primal)
        by_count = [0] * (m + 1)
        both = neither = 0
        for mask in range(1 << m):
            is_open = [bool((mask >> q) & 1) for q in range(m)]
            across, blocked = lattice_crossings(n, is_open, primal, dual)
            both += across and blocked
            neither += (not across) and (not blocked)
            if across:
                by_count[bin(mask).count("1")] += 1
        total = sum(by_count)
        symmetric = all(by_count[q] + by_count[m - q] == math.comb(m, q) for q in range(m + 1))
        both_total, neither_total = both_total + both, neither_total + neither
        ok = ok and both == 0 and neither == 0 and 2 * total == 1 << m and symmetric
        rows.append(f"n = {n}: {m} bonds, {total} of {1 << m} configurations cross")
    check(
        "F4",
        ok,
        "bond percolation on the rectangle of n + 1 by n points, each bond open or closed, leaving out the bonds that lie in its left and right sides (they cannot help a "
        "crossing from left to right). In every configuration exactly one of two things happens: open bonds join left to right, or the dual bonds across closed bonds join "
        f"bottom to top (both: {both_total} configurations, neither: {neither_total}). That holds at any density, and at any density the dual rectangle is the same rectangle turned. "
        "What is special at one half is that a bond is as likely closed as open, so the two events have equal odds: exactly half the configurations cross. "
        + "; ".join(rows) + ". With k of the m bonds open the crossing counts satisfy c(k) + c(m - k) = C(m, k), so P(p) + P(1 - p) = 1 exactly",
    )

    # F5: away from one half the crossing probability goes to 0 or 1 as the rectangle grows; at one half it stays put
    rng = Rng(1980)
    table = {}
    violations = 0
    samples = 300
    for n in (6, 12, 24):
        primal, dual = lattice_edges(n)
        left, right = [j for j in range(n)], [n * n + j for j in range(n)]
        for p in (0.4, 0.5, 0.6):
            hits = 0
            for trial in range(samples):
                is_open = [rng.uniform() < p for _ in primal]
                if n == 6:
                    across, blocked = lattice_crossings(n, is_open, primal, dual)
                    violations += across == blocked
                else:
                    across = lattice_joined((n + 1) * n, primal, is_open, left, right)
                hits += across
            table[(n, p)] = hits / samples
    sigma = 0.5 / math.sqrt(samples)
    check(
        "F5",
        violations == 0
        and all(abs(table[(n, 0.5)] - 0.5) < 3.5 * sigma for n in (6, 12, 24))
        and table[(6, 0.4)] > table[(12, 0.4)] > table[(24, 0.4)] and table[(6, 0.6)] < table[(12, 0.6)] < table[(24, 0.6)]
        and table[(24, 0.4)] < 0.1 and table[(24, 0.6)] > 0.9,
        f"simulated, {samples} rectangles at each size and density (sampling error about {sigma:.2f}): the fraction that cross at density 0.4, 0.5, 0.6 is "
        + "; ".join(f"n = {n}: {table[(n, 0.4)]:.3f}, {table[(n, 0.5)]:.3f}, {table[(n, 0.6)]:.3f}" for n in (6, 12, 24))
        + f". Below one half it falls toward 0 with size, above it rises toward 1, at one half it stays at 1/2. (In the {3 * samples} simulated rectangles of size 6, "
        f"where both crossings were tested, exactly one happened every time: {violations} exceptions)",
    )


# ====================================================================================================
# section G: tipping

TITLE_TIPPING = "G. Two tipping points: avalanches at branching ratio one, deep networks at the edge of chaos"


# ---- avalanches: every event sets off a Poisson number of further events, m on average


def tipping_borel(m: float, s: int) -> float:
    """Probability that the avalanche has exactly s events in all (Borel's law)."""
    return math.exp(-m * s + (s - 1) * math.log(m * s) - math.lgamma(s + 1))


def tipping_extinction(m: float) -> float:
    """Probability that the avalanche ever stops: the least root of q = exp(m (q - 1))."""
    q = 0.0
    for _ in range(20000):
        q = math.exp(m * (q - 1))
    return q


def tipping_poisson(rng: Rng, floor: float) -> int:
    """A Poisson number with mean m, given floor = exp(-m) (Knuth's method, uniform draws only)."""
    k = 0
    p = rng.uniform()
    while p > floor:
        k += 1
        p *= rng.uniform()
    return k


def tipping_avalanche(rng: Rng, m: float, cap: int) -> int:
    """Total size of one avalanche, stopped once `cap` events have been set off."""
    floor = math.exp(-m)
    waiting, total = 1, 1
    while waiting and total < cap:
        k = tipping_poisson(rng, floor)
        waiting += k - 1
        total += k
    return min(total, cap)


# ---- a deep random network: h -> W tanh(h) + b, weights of variance sw2 / width, biases of variance sb2

tipping_STEP = 0.1
tipping_NODES = [(-8 + tipping_STEP * j) for j in range(161)]
tipping_WEIGHTS = [tipping_STEP * math.exp(-0.5 * z * z) / math.sqrt(2 * PI) for z in tipping_NODES]


def tipping_gauss_mean(f) -> float:
    """The mean of f(z) over a standard normal z."""
    return sum(w * f(z) for z, w in zip(tipping_NODES, tipping_WEIGHTS))


def tipping_length(sw2: float, sb2: float) -> float:
    """The mean square q of a unit's input deep in a wide network: q = sw2 E[tanh(sqrt(q) z)^2] + sb2."""
    q = 1.0
    for _ in range(400):
        r = math.sqrt(q)
        q = sw2 * tipping_gauss_mean(lambda z: math.tanh(r * z) ** 2) + sb2
    return q


def tipping_gain(sw2: float, sb2: float) -> float:
    """By how much one layer multiplies the squared distance between two nearby inputs:
    chi = sw2 E[tanh'(sqrt(q) z)^2]."""
    r = math.sqrt(tipping_length(sw2, sb2))
    return sw2 * tipping_gauss_mean(lambda z: (1 / math.cosh(r * z)) ** 4)


def tipping_overlap(sw2: float, sb2: float, q: float, c: float) -> float:
    """What one wide layer does to two inputs whose units have mean square q and correlation c:
    the new mean product, sw2 E[tanh(u1) tanh(u2)] + sb2, by a double integral."""
    r = math.sqrt(q)
    rest = math.sqrt(max(0.0, 1 - c * c))
    total = 0.0
    for z1, w1 in zip(tipping_NODES, tipping_WEIGHTS):
        inner = 0.0
        for z2, w2 in zip(tipping_NODES, tipping_WEIGHTS):
            inner += w2 * math.tanh(r * (c * z1 + rest * z2))
        total += w1 * math.tanh(r * z1) * inner
    return sw2 * total + sb2


def tipping_network(sw2s: tuple, sb2: float, width: int, depth: int, seed: int, eps: float = 1e-5) -> dict:
    """Send two inputs a distance eps apart through one random network at each weight variance in
    sw2s (the same Gaussian draws, scaled), and return the squared distance after each layer."""
    rng = Rng(seed)
    x = [rng.gauss() for _ in range(width)]
    y = [a + eps * rng.gauss() for a in x]
    state = {s: (x, y) for s in sw2s}
    trace = {s: [] for s in sw2s}
    sb = math.sqrt(sb2)
    for layer in range(depth):
        rows = [[rng.gauss() for _ in range(width)] for _ in range(width)]
        bias = [sb * rng.gauss() for _ in range(width)]
        for s in sw2s:
            sw = math.sqrt(s / width)
            hx, hy = state[s]
            ax = [math.tanh(v) for v in hx] if layer else hx
            ay = [math.tanh(v) for v in hy] if layer else hy
            nx = [sw * sum(map(mul, row, ax)) + b for row, b in zip(rows, bias)]
            ny = [sw * sum(map(mul, row, ay)) + b for row, b in zip(rows, bias)]
            state[s] = (nx, ny)
            trace[s].append(sum((a - b) ** 2 for a, b in zip(nx, ny)) / width)
    return trace


def section_tipping() -> None:
    # G1: exactly at branching ratio one the sizes follow a power law with no scale
    ratios = [(s, tipping_borel(1.0, s) * s ** 1.5 * math.sqrt(2 * PI)) for s in (10, 100, 1000, 10000)]
    upto = 10 ** 6
    partial = sum(tipping_borel(1.0, s) for s in range(1, upto + 1))
    tail_law = math.sqrt(2 / (PI * upto))
    check(
        "G1",
        all(abs(r - (1 - 1 / (12 * s) + 1 / (288 * s * s))) < 1e-5 for s, r in ratios) and abs((1 - partial) / tail_law - 1) < 1e-5,
        "avalanches in which every event sets off a Poisson number of further events, one on average: the chance of exactly s events in all is e^(-s) s^(s-1)/s! "
        "(Borel's law), and against the pure power law s^(-3/2)/sqrt(2 pi) it stands at "
        + ", ".join(f"{r:.5f} for s = {s}" for s, r in ratios)
        + f". No size is typical: the chance of more than a million events is still {1 - partial:.6f}, which is sqrt(2/(pi s)) = {tail_law:.6f}, and the mean size is infinite",
    )

    # G2: off the edge, on either side, a scale appears
    rows = []
    ok = True
    for m in (0.9, 0.99):
        probs = [tipping_borel(m, s) for s in range(1, 400001)]
        total, mean = sum(probs), sum(s * p for s, p in enumerate(probs, start=1))
        cutoff = 1 / (m - 1 - math.log(m))
        ok = ok and abs(total - 1) < 1e-9 and abs(mean * (1 - m) - 1) < 1e-6
        rows.append(f"m = {m}: mean size {mean:.2f} = 1/(1 - m), sizes cut off beyond about {cutoff:.0f}")
    exact_ratio = max(
        abs(tipping_borel(m, s) / tipping_borel(1.0, s) * m * math.exp(s * (m - 1 - math.log(m))) - 1) for m in (0.9, 0.99, 1.2) for s in (1, 10, 100, 1000)
    )
    m_over = 1.2
    q = tipping_extinction(m_over)
    total_over = sum(tipping_borel(m_over, s) for s in range(1, 20001))
    cut_ratio = (1 / (0.99 - 1 - math.log(0.99))) / (1 / (0.9 - 1 - math.log(0.9)))
    # the mirror: the avalanches that stop at m are, exactly, the avalanches at m* = m q, and m e^(-m) = m* e^(-m*)
    m_star = m_over * q
    mirror_gap = max(abs(tipping_borel(m_over, s) / (q * tipping_borel(m_star, s)) - 1) for s in (1, 2, 5, 20, 100, 500))
    wrong_star = abs(tipping_borel(m_over, 100) / (q * tipping_borel(m_star + 0.02, 100)) - 1)
    check(
        "G2",
        ok and exact_ratio < 1e-9 and abs(total_over - q) < 1e-9 and abs(q - math.exp(m_over * (q - 1))) < 1e-12 and 100 < cut_ratio < 110
        and mirror_gap < 1e-9 and wrong_star > 0.05 and abs(m_over * math.exp(-m_over) - m_star * math.exp(-m_star)) < 1e-12,
        "off the edge a scale appears. With m further events on average, the chance of size s is the m = 1 law times e^(-s (m - 1 - ln m))/m, exactly "
        f"(checked to {tiny(exact_ratio)}). Below one: " + "; ".join(rows)
        + f", so ten times nearer the edge the cutoff is {cut_ratio:.0f} times further out. Above one, at m = {m_over}: the sizes of the avalanches that stop add up to only "
        f"{total_over:.6f}, which is the root q = {q:.6f} of q = e^(m (q - 1)); the missing {1 - q:.4f} is the chance of an avalanche that never stops. "
        f"There is a mirror here too: the avalanches that do stop at m = {m_over} have exactly the sizes of all avalanches at m* = m q = {m_star:.6f} "
        f"(chance of each size the same to {tiny(mirror_gap)}; with m* off by 0.02 the chance of size 100 is off by {wrong_star:.2f} of itself), "
        "where m e^(-m) = m* e^(-m*), and the only m that is its own image is 1",
    )

    # G3: the same three regimes, simulated
    rng = Rng(2003)
    runs = 20000
    sizes = [tipping_avalanche(rng, 1.0, 2000) for _ in range(runs)]
    rows = []
    ok = True
    for s0 in (10, 100, 1000):
        exact = 1 - sum(tipping_borel(1.0, s) for s in range(1, s0))
        seen = sum(1 for s in sizes if s >= s0) / runs
        sigma = math.sqrt(exact * (1 - exact) / runs)
        ok = ok and abs(seen - exact) < 4 * sigma
        rows.append(f"at least {s0} events: {seen:.4f} of them, exact {exact:.4f}")
    over = [tipping_avalanche(rng, m_over, 400) for _ in range(2000)]
    never = sum(1 for s in over if s >= 400) / 2000
    under = [tipping_avalanche(rng, 0.9, 10 ** 6) for _ in range(4000)]
    mean_under = sum(under) / 4000
    check(
        "G3",
        ok and abs(never - (1 - q)) < 0.04 and abs(mean_under - 10) < 1.0 and max(under) < 5000,
        f"simulated. At m = 1, {runs} avalanches: " + "; ".join(rows)
        + f". At m = {m_over}, 2000 avalanches: {never:.4f} of them were still running after 400 events (chance of never stopping: {1 - q:.4f}). "
        f"At m = 0.9, 4000 avalanches: mean size {mean_under:.2f} (exact 10), largest {max(under)}",
    )

    # G4: a deep random network has an edge too, and it can be computed
    sb2 = 0.05
    edge = bisect(lambda v: tipping_gain(v, sb2) - 1, 1.0, 3.0, tol=1e-7)
    settings = (1.0, edge, 3.0)
    gains = {s: tipping_gain(s, sb2) for s in settings}
    # a second route to chi that does not use the formula: move the correlation of two inputs from 1 to 1 - d
    # and see how far one layer lets it fall
    d = 1e-3
    direct = {}
    for s in settings:
        q = tipping_length(s, sb2)
        direct[s] = (q - tipping_overlap(s, sb2, q, 1 - d)) / (q * d)
    route_gap = max(abs(direct[s] / gains[s] - 1) for s in settings)
    no_bias = [tipping_gain(v, 0.0) for v in (0.5, 0.9)]
    depth_scale = {s: (1 / abs(math.log(gains[s])) if abs(gains[s] - 1) > 1e-4 else float("inf")) for s in settings}
    check(
        "G4",
        abs(edge - 1.76) < 0.01  # 1.76: the value I remember from the literature for this bias (external, from memory)
        and gains[1.0] < 0.8 and gains[3.0] > 1.15 and abs(gains[edge] - 1) < 1e-5 and route_gap < 0.01
        and max(abs(no_bias[0] - 0.5), abs(no_bias[1] - 0.9)) < 1e-9,
        "a deep network with random weights, each layer h -> W tanh(h) + b, weights of variance v/width and biases of variance 0.05. In the limit of great width one layer "
        "multiplies the squared distance between two nearby inputs by chi = v E[tanh'(sqrt(q) z)^2], q the settled mean square of h: "
        f"chi = {gains[1.0]:.4f} at v = 1 (differences die out: order), {gains[3.0]:.4f} at v = 3 (they grow: chaos), and exactly 1 at v = {edge:.4f}, the edge. "
        f"A second route that does not use that formula, lowering the correlation of two inputs from 1 to {1 - d} and integrating what one layer does to it, gives "
        f"{direct[1.0]:.4f}, {direct[edge]:.4f}, {direct[3.0]:.4f} (within {route_gap:.1e} of the formula; the difference is the size of the step). "
        f"The number of layers over which a difference changes by a factor e is 1/|ln chi|: {depth_scale[1.0]:.1f} at v = 1, {depth_scale[3.0]:.1f} at v = 3, unbounded at the edge. "
        f"With no bias, q settles at 0 for v < 1 and chi is v itself ({no_bias[0]:.4f} at v = 0.5, {no_bias[1]:.4f} at v = 0.9)",
    )

    # G5: and real random networks of modest width do what the limit says
    width, depth, seeds = 200, 24, (11, 12, 13)
    measured = {s: [] for s in settings}
    for seed in seeds:
        trace = tipping_network(settings, sb2, width, depth, seed)
        for s in settings:
            measured[s].append((trace[s][-1] / trace[s][4]) ** (1 / (depth - 5)))
    means = {s: sum(v) / len(v) for s, v in measured.items()}
    spread = max(max(v) - min(v) for v in measured.values())
    check(
        "G5",
        all(abs(means[s] / gains[s] - 1) < 0.07 for s in settings) and means[1.0] < 0.85 and means[3.0] > 1.1,
        f"simulated: three random networks of width {width} and depth {depth}, two inputs 1e-5 apart, the factor per layer by which their squared distance changes "
        f"(layers 5 to {depth}, averaged over the three): {means[1.0]:.3f} at v = 1 (the limit says {gains[1.0]:.3f}), {means[edge]:.3f} at the edge (1.000), "
        f"{means[3.0]:.3f} at v = 3 ({gains[3.0]:.3f}). The three networks differ among themselves by up to {spread:.3f}: at this width the edge is a few percent wide",
    )


# ====================================================================================================
# section H: series

TITLE_SERIES = "H. Reaching the line from the primes' side: one series gets there, the product does not"


def series_sieve(limit: int) -> tuple[list[int], list[int]]:
    """Moebius function up to limit, and the primes up to limit."""
    mu = [1] * (limit + 1)
    mu[0] = 0
    is_prime = bytearray([1]) * (limit + 1)
    is_prime[0] = is_prime[1] = 0
    primes = []
    for p in range(2, limit + 1):
        if is_prime[p]:
            primes.append(p)
            for m in range(2 * p, limit + 1, p):
                is_prime[m] = 0
            for m in range(p, limit + 1, p):
                mu[m] = -mu[m]
            for m in range(p * p, limit + 1, p * p):
                mu[m] = 0
    return mu, primes


def series_partial(s: complex, mu: list[int], primes: list[int], marks: list[int]) -> list[tuple[int, complex, complex]]:
    """At each mark X: the Moebius sum over n <= X of mu(n) n^(-s), and the log of the Euler product over p <= X."""
    out = []
    total = 0j
    n = 1
    log_product = 0j
    k = 0
    for mark in marks:
        while n <= mark:
            if mu[n]:
                total += mu[n] * cmath.exp(-s * math.log(n))
            n += 1
        while k < len(primes) and primes[k] <= mark:
            log_product -= cmath.log(1 - cmath.exp(-s * math.log(primes[k])))
            k += 1
        out.append((mark, total, log_product))
    return out


def section_series() -> None:
    limit = 10 ** 6
    marks = [10 ** 3, 10 ** 4, 10 ** 5, 10 ** 6]
    mu, primes = series_sieve(limit)

    s = 0.75 + 5j
    z = zeta(s)
    rows = series_partial(s, mu, primes, marks)
    moebius = [abs(total - 1 / z) for _, total, _ in rows]
    product = [abs(lp - cmath.log(z)) for _, _, lp in rows]
    leading = limit ** (1 - s.real) / (abs(1 - s) * math.log(limit))  # size of li(X^(1-s)), the pole's contribution
    check(
        "H1",
        moebius[-1] < 0.012 and moebius[-1] < 0.5 * moebius[0] and all(b > a for a, b in zip(product, product[1:])) and abs(product[-1] - leading) < 0.1 * leading,
        f"at s = 0.75 + 5i, between the pole and the line, with terms up to 10^3, 10^4, 10^5, 10^6: the Moebius series' distance from 1/zeta goes "
        f"{', '.join(f'{v:.3f}' for v in moebius)}; the log of (Euler product / zeta) goes {', '.join(f'{v:.3f}' for v in product)}, "
        f"growing as the pole says it must (leading size at 10^6: {leading:.3f})",
    )

    s2 = 2 + 5j
    z2 = zeta(s2)
    rows2 = series_partial(s2, mu, primes, marks)
    check(
        "H2",
        abs(rows2[-1][1] - 1 / z2) < 1e-5 and abs(rows2[-1][2] - cmath.log(z2)) < 1e-5,
        f"control, to the right of the pole at s = 2 + 5i: both converge (Moebius series off by {abs(rows2[-1][1] - 1 / z2):.0e}, "
        f"log of the product off by {abs(rows2[-1][2] - cmath.log(z2)):.0e} at 10^6)",
    )


def main() -> int:
    known = "A B C D E F G H".split()
    flags = [a for a in sys.argv[1:] if a.startswith("-")]
    wanted = [a.upper() for a in sys.argv[1:] if not a.startswith("-")]
    bad = [a for a in wanted if a not in known] + [f for f in flags if f != "-v"]
    if bad:
        print("not understood: " + " ".join(bad) + ". Sections are " + " ".join(known) + ", given as separate letters (edge.py C E); the only flag is -v.")
        return 2
    for letter, title, fn in (
        ("A", TITLE_DENSITY, section_density),
        ("B", TITLE_COINS, section_coins),
        ("C", TITLE_FLOW, section_flow),
        ("D", TITLE_ZEROS, section_zeros),
        ("E", TITLE_MIRROR, section_mirror),
        ("F", TITLE_LATTICE, section_lattice),
        ("G", TITLE_TIPPING, section_tipping),
        ("H", TITLE_SERIES, section_series),
    ):
        if wanted and letter not in wanted:
            continue
        print(title)
        try:
            fn()
        except Exception as err:  # the checks of this section not yet printed are lost; say so and go on
            check(letter + " (section stopped)", False, f"the section raised {type(err).__name__} ({err}) before finishing")
    failed = [name for ok, name, _ in RESULTS if not ok]
    print(f"{len(RESULTS)} checks, {len(failed)} failed" + (": " + ", ".join(failed) if failed else ""))
    return 1 if failed or not RESULTS else 0


if __name__ == "__main__":
    sys.exit(main())
