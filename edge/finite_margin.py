"""Count real zeros of the backward heat flow on 4 <= x < 100000.

Run with Python 3, numpy, scipy and mpmath. Uses the Hardy Z evaluator in edge.py.
"""

from math import ceil, log, pi, sqrt

import numpy as np
from mpmath import mp
from scipy.integrate import quad
from scipy.interpolate import make_interp_spline
from scipy.ndimage import correlate1d
from scipy.special import loggamma

from edge import zeros_cubic_root, zeros_make_z, zeros_RS_TABLE


TOP = 100_000
TIMES = (0, .0000625, .000107, .000109, .000125, .00025, .0005, .00065, .001, .002, .004, .008)


def crossings(values, refine=False):
    """Sign-change locations in grid units, plus any sub-cell pairs."""
    negative = values < 0
    i = np.flatnonzero(negative[:-1] != negative[1:])
    roots = i + values[i] / (values[i] - values[i+1])
    if refine:
        # Resolve the original gaps accurately for the gap-only prediction.
        for k, j in enumerate(i):
            if 0 < j < len(values) - 2:
                u = zeros_cubic_root(*values[j-1:j+3])
                if 0 < u < 1:
                    roots[k] = j + u
    magnitude = abs(values)
    # If the three samples have one sign, a local quadratic may still have
    # two roots. The refined run uses smaller cells and an offset grid.
    i = 1 + np.flatnonzero((negative[:-2] == negative[1:-1]) &
                           (negative[1:-1] == negative[2:]) &
                           (magnitude[1:-1] <= magnitude[:-2]) &
                           (magnitude[1:-1] < magnitude[2:]))
    a = (values[i-1] + values[i+1]) / 2 - values[i]
    b = (values[i+1] - values[i-1]) / 2
    d = b*b - 4*a*values[i]
    keep = (d > 0) & (a != 0)
    if np.any(keep):
        i, a, b, d = i[keep], a[keep], b[keep], np.sqrt(d[keep])
        r1, r2 = (-b-d) / (2*a), (-b+d) / (2*a)
        inside = (abs(r1) < 1) & (abs(r2) < 1)
        roots = np.concatenate((roots, (i+r1)[inside], (i+r2)[inside]))
    return np.sort(roots)


def scan(coarse, fine, offset, top=TOP, times=TIMES):
    z = zeros_make_z(top + 4, zeros_RS_TABLE)
    output = {b: [] for b in times}
    kernels = {}
    for b in times:
        if b == 0:
            continue
        radius = ceil(10 * sqrt(b / 2) * fine)
        u = np.arange(-radius, radius+1) / fine
        # G_b(u) times the tilt that undoes the scaling of our input samples.
        weights = np.exp(-u*u/b - pi*u/4)
        kernels[b] = weights / weights.sum()

    for lo in range(4, top, 512):
        hi = min(lo + 512, top)
        x = lo - 2 + (np.arange((hi-lo+4)*coarse+1) + offset) / coarse
        # A common scalar is immaterial. Keep the variation in the completed
        # xi prefactor and remove its exponential decay to avoid underflow.
        log_weight = np.log(x*x + .25) + loggamma(.25 + .5j*x).real + pi*x/4
        initial = np.exp(log_weight - log_weight[len(x)//2]) * np.fromiter(map(z, x), float)
        spline = make_interp_spline(x, initial, k=7)
        grid = lo - 1 + (np.arange((hi-lo+2)*fine+1) + offset) / fine
        samples = spline(grid)
        for b in times:
            values = correlate1d(samples, kernels[b]) if b else samples
            roots = grid[0] + crossings(values, refine=(b == 0)) / fine
            output[b].extend(roots[(lo <= roots) & (roots < hi)])
    return {b: np.array(roots) for b, roots in output.items()}


def losses(initial, current, top):
    # Group nearby initial roots. Place counting boundaries halfway across
    # gaps wider than 0.30 and check that no evolved root nears a boundary.
    initial = initial[initial < top]
    current = current[current < top]
    wide = np.flatnonzero(np.diff(initial) > .30)
    cuts = np.r_[4, (initial[wide] + initial[wide+1]) / 2, top]
    if min(top - initial[-1], top - current[-1]) < .03:
        raise ArithmeticError("Choose a height cap farther from a zero")
    ix = np.searchsorted(current, cuts[1:-1])
    margins = np.minimum(current[ix] - cuts[1:-1], cuts[1:-1] - current[ix-1])
    if np.min(margins) < .03:
        raise ArithmeticError("A counting boundary approaches an evolved zero")
    old_counts = np.diff(np.searchsorted(initial, cuts))
    new_counts = np.diff(np.searchsorted(current, cuts))
    vanished = old_counts - new_counts
    if np.any(vanished < 0) or np.any(vanished % 2):
        raise ArithmeticError("Unmatched real zero at a counting boundary")
    groups = np.flatnonzero(vanished)
    if not len(groups):
        return 0, None
    g = groups[0]
    first = initial[(initial >= cuts[g]) & (initial < cuts[g+1])]
    if len(first) != 2:
        raise ArithmeticError("First loss is in a group of more than two roots")
    return int(vanished.sum() // 2), first.mean()


def predicted(b, lo, hi):
    # Sine-kernel small-gap prediction, using ordinary zeta height.
    mass = quad(lambda x: (log(x/(2*pi))/(2*pi))**4, max(2*pi, lo), hi)[0]
    return pi*pi/9 * (2*b)**1.5 * mass


def local_witness(midpoint):
    """Recover one missing pair from direct high-precision samples of xi."""
    with mp.workdps(35):
        centre = mp.mpf(str(midpoint))
        step = mp.mpf(".002")
        offsets = [j * step for j in range(-60, 61)]
        gamma_ref = mp.loggamma(mp.mpc(".25", centre / 2)).real
        samples = []
        for y in offsets:
            h = centre + y
            weight = mp.exp(mp.loggamma(mp.mpc(".25", h / 2)).real - gamma_ref)
            samples.append((h*h + mp.mpf(".25")) / centre**2 * weight * mp.siegelz(h))

        def flow(x, b):
            terms = [v * mp.exp(-(x-y)**2/b) for v, y in zip(samples, offsets)]
            value = mp.fsum(terms)
            slope = 2/b * mp.fsum((y-x)*v for v, y in zip(terms, offsets))
            return value, slope

        x, bcrit = mp.findroot(flow, (0, mp.mpf(".00011")))
        b = mp.mpf(".000125")
        off = mp.findroot(lambda z: flow(z, b)[0], x + mp.j * mp.sqrt((b-bcrit)/2),
                          solver="newton", df=lambda z: flow(z, b)[1])
        extremum = mp.findroot(lambda z: flow(z, b)[1], x, solver="newton")
        curvature = mp.diff(lambda z: flow(z, b)[1], extremum)
        inferred = mp.sqrt(2 * flow(extremum, b)[0] / curvature)
        if not (mp.mpf(".000107") < bcrit < mp.mpf(".000109") and off.imag > 0
                and abs(off-x) < .01 and abs(extremum-x) < .01
                and abs(inferred / off.imag - 1) < mp.mpf(".0001")):
            raise ArithmeticError("Local witness disagrees with the scan or the real-axis estimate")
        print("collision height, backward time:", mp.nstr(centre+x, 16), mp.nstr(bcrit, 12))
        print("complex root at b=.000125:", mp.nstr(centre+off, 17))
        print("imaginary distance estimated on the real line:", mp.nstr(inferred, 12))


def report(runs):
    for b in TIMES:
        a, c = (run[b] for run in runs)
        if len(a) != len(c) or max(abs(a - c)) > .005:
            raise ArithmeticError(f"Refinement disagrees on a root at backward time {b}")
    # Independently obtained with mpmath.nzeros, which counts zeros in the strip.
    for top, expected in ((30_000, 35_673), (TOP, 138_069)):
        initial = runs[1][0]
        initial = initial[initial < top]
        if len(initial) != expected:
            raise ArithmeticError(f"Zero count at time zero disagrees below {top}")
        gaps = np.diff(initial)
        print(f"\nHeight < {top}, {len(initial)} initial zeros.")
        print("backward time   pairs lost   first initial midpoint   gap-only count   model mean")
        for b in TIMES:
            first, second = [losses(run[0], run[b], top) for run in runs]
            if first[0] != second[0] or abs((first[1] or 0) - (second[1] or 0)) > .005:
                raise ArithmeticError("Root counts or first pair disagree across grids")
            midpoint = f"{second[1]:.3f}" if second[1] is not None else "none"
            gap_count = np.count_nonzero(gaps**2 < 2*b)
            print(f"{b:13.7f} {second[0]:12d} {midpoint:24} {gap_count:8d} {predicted(b, 4, top):15.3f}")
    _, midpoint = losses(runs[1][0], runs[1][.000125], TOP)
    local_witness(midpoint)


if __name__ == "__main__":
    report([scan(12, 160, 0), scan(16, 256, .5)])
