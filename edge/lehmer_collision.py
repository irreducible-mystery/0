"""Follow the pair near zeta height 17143.8 under the de Bruijn-Newman flow.

Run with Python 3 and mpmath. Heights are ordinary zeta ordinates. The time
t is in the literature's convention, so ∂F/∂t = -(∂²F/∂x²)/4 here.
"""

from mpmath import mp


def taylor_collision():
    """Cross-check the Gaussian integral using the heat flow of a polynomial."""
    with mp.workdps(40):
        centre = mp.mpf("17143.804")
        radius = mp.mpf(".3")
        count, degree = 40, 20
        phases = [mp.expjpi(2 * mp.mpf(j) / count) for j in range(count)]
        gamma_scale = mp.loggamma(mp.mpc(".25", centre / 2)).real
        values = []
        for phase in phases:
            s = mp.mpf(".5") + mp.j * (centre + radius * phase)
            log_factor = mp.loggamma(s / 2) - gamma_scale - (s / 2) * mp.log(mp.pi)
            values.append(s * (s - 1) * mp.exp(log_factor) * mp.zeta(s))

        # Cauchy's formula recovers the Taylor coefficients from circle samples.
        coefficients = []
        for k in range(degree + 1):
            coefficient = mp.fsum(v * phase**(-k) for v, phase in zip(values, phases))
            coefficients.append(coefficient.real / (count * radius**k))

        def polynomial_flow(x, t):
            # Moments of a Gaussian with mean x and variance -t/2 give the
            # exact flow of each monomial. Its x derivative is k times M_(k-1).
            moments = [mp.mpf(1), x]
            for k in range(2, degree + 1):
                moments.append(x * moments[-1] - (k - 1) * (t / 2) * moments[-2])
            value = mp.fdot(coefficients, moments)
            slope = mp.fsum(k * coefficients[k] * moments[k-1] for k in range(1, degree + 1))
            return value, slope

        x, t = mp.findroot(polynomial_flow, (0, -mp.mpf(".0006")))
        return centre + x, t


def trace(digits, step, radius):
    with mp.workdps(digits):
        centre = mp.mpf("17143.804")
        step = mp.mpf(step)
        log_gamma_ref = mp.loggamma(mp.mpc("0.25", centre / 2)).real

        def initial(offset):
            y = centre + offset
            # Xi(y) up to one common nonzero factor. Its gamma envelope at this
            # height underflows a float. Keep the variation across the grid.
            log_gamma = mp.loggamma(mp.mpc("0.25", y / 2)).real
            envelope = (y**2 + mp.mpf("0.25")) / (centre**2 + mp.mpf("0.25"))
            return envelope * mp.exp(log_gamma - log_gamma_ref) * mp.siegelz(y)

        left = mp.findroot(initial, (-mp.mpf(".02"), -mp.mpf(".015")))
        right = mp.findroot(initial, (mp.mpf(".015"), mp.mpf(".02")))
        estimate = -(right - left)**2 / 2
        offsets = [j * step for j in range(-radius, radius + 1)]
        samples = [initial(y) for y in offsets]

        def flow(x, t):
            # For t < 0 the solution is the Gaussian convolution of Xi.
            # The derivative below differentiates the kernel with respect to x.
            width = -t
            scale = step / mp.sqrt(mp.pi * width)
            terms = [v * mp.exp(-(x - y)**2 / width) for y, v in zip(offsets, samples)]
            value = scale * mp.fsum(terms)
            slope = scale * (2 / width) * mp.fsum((y - x) * v for y, v in zip(offsets, terms))
            return value, slope

        x, t = mp.findroot(flow, ((left + right) / 2, estimate))
        delta = mp.mpf("0.00001")
        split = mp.sqrt(delta / 2)

        def root_at(time, start):
            return mp.findroot(lambda z: flow(z, time)[0], start,
                               df=lambda z: flow(z, time)[1], solver="newton")

        # Continue each original root, seeding each solve with its last position.
        before = [left, right]
        for time in (t / 4, t / 2, 3 * t / 4, t + delta):
            before = [root_at(time, seed) for seed in before]
            if not before[0] < x < before[1]:
                raise ArithmeticError("Lost the two distinct real roots during continuation")
        after = root_at(t - delta, x + mp.j * split)
        # A simple collision has squared separation 2*|t-t_c| to leading
        # order. Check both sides to catch a sign or a factor of four in time.
        separations = [before[1] - before[0], 2 * after.imag]
        if after.imag <= 0 or any(abs(g**2 / delta - 2) > mp.mpf(".001") for g in separations):
            raise ArithmeticError("Unexpected local splitting at the double zero")

        return {
            "lower zero at t = 0": centre + left,
            "upper zero at t = 0": centre + right,
            "gap estimate": estimate,
            "collision t": t,
            "collision height": centre + x,
            "lower zero at t + 1e-5": centre + before[0],
            "upper zero at t + 1e-5": centre + before[1],
            "complex zero at t - 1e-5": centre + after,
        }


def main():
    coarse = trace(28, ".005", 36)
    fine = trace(45, ".0025", 96)
    taylor_height, taylor_time = taylor_collision()
    with mp.workdps(45):
        if max(abs(taylor_height - fine["collision height"]),
               abs(taylor_time - fine["collision t"])) > mp.mpf("1e-12"):
            raise ArithmeticError("Taylor and Gaussian collision estimates disagree")
        for label, value in fine.items():
            if abs(value - coarse[label]) > mp.mpf("1e-12"):
                raise ArithmeticError(f"Grid refinement disagrees for {label}")
            print(f"{label:26} {mp.nstr(value, 19)}")
        relative = abs(fine["collision t"] / fine["gap estimate"]) - 1
        print(f"extra backward time        {mp.nstr(100 * relative, 8)}%")


if __name__ == "__main__":
    main()
