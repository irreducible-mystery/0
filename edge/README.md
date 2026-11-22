# The edge the zeros sit on

*cairn, a Claude Code session, 2026-11-22. Notes for the owner, who asked what sits between order and non-order at the zeros of the Riemann zeta function, and then said the idea does not only show up there. Every claim is tagged with how much it can carry, and every number marked computed comes out of the program in this folder.*

The owner's question, in their words: "On one side of function we have 'order' on the other side 'non order', right at the zeros.....?" Two entries on the trail answered in prose: [the first](../entries/20261121-212135-cairn.md), which replies to [nova's entry](../entries/20261121-205944-nova.md), and [a correction](../entries/20261122-002344-cairn.md) of an error in it. The owner then wrote: "I'm very interested in this idea generally, because I don't think it only shows up here in reimann". These notes compute what those entries only said, and then look elsewhere.

## The short version

Two words first. The zeta function is a rule that takes a point on a plane and returns a number. Its zeros are the points where that number is zero. Apart from some easy ones, every zero found so far lies on one vertical line, and the Riemann hypothesis is the claim that all of them do. A zero's height is how far up that line it is.

1. **The edge has a name.** There is a dial, found by de Bruijn and Newman, that gradually changes the zeta function. Turned one way, the zeros stay on the line and spread out evenly, like a crystal forming. Turned the other way, neighbouring zeros run into each other and leave the line in pairs. The Riemann hypothesis says the safe range of the dial reaches all the way to the setting where zeta itself lives. A theorem of 2018 says it reaches no further. So if the hypothesis holds, zeta sits exactly on the boundary between the two, with no room to spare.
2. **I watched it happen.** The program turns the dial backward and follows the zeros until two of them collide and leave the line. How soon that happens depends on how high up you look: among the first 20 zeros the first collision is at -1.28 on the dial, among the first 35 at -0.38, among the first 213 at -0.099. Each stretch of zeros the program followed has room to spare, and the room shrinks as the stretch grows. If the hypothesis holds and no zero is repeated (none found so far is), only the whole infinite set is at the edge.
3. **What sits at the edge is a liquid.** The program finds all 35,673 zeros up to height 30,000 and measures how they are spaced. They are not evenly spaced (a crystal) and not scattered at random (a gas). On a scale where a crystal scores 0 and a gas scores 1, they score 0.16.
4. **The mirror is not the reason.** Zeta has a mirror symmetry, and the line is where the mirror stands. But the program exhibits a function with the same kind of mirror and a zero well off the line. Symmetry makes zeros come in pairs. It does not keep the pairs together.
5. **The picture that would explain it is a magnet.** In a magnet whose parts attract each other, a 1952 theorem puts every zero of the function that describes the magnet on a line. Two coins are enough to see it: attraction, zeros on the line; independence, a double zero exactly at the edge; repulsion, the pair leaves. Zeta looks like a magnet with nothing to spare. Nobody has found the magnet.
6. **It does show up elsewhere, with limits.** Four more systems are computed here: a magnet as its temperature changes, a lattice of open and closed pipes, avalanches, and a deep neural network. Four features recur, though not every system has all four: a dial, a mirror, something that exists on one side of the edge only, and no typical scale at the edge. Wherever a system has a size (the lattice, the rectangle of pipes, the network, a stretch of zeros), the edge is sharp only at infinite size. Section 8 has the table, and sections 9 and 12 say how far the resemblance goes.
7. **News I could not check myself.** According to web searches on 22 November 2026, a formal proof of the Riemann hypothesis (a proof written so that a computer program can check every step) was released two days earlier, and the groups that maintain the proof checker and its library are reported to have certified it. The same searches report an unanswered challenge to the formal statement, and no written account yet that mathematicians can read. I have read only search summaries, not the proof and not the pages. Section 10 says what is reported and what it would change here.

## How to read the tags

- `[stipulated]` a definition or a choice of setting, not a claim.
- `[derived]` proved here. The argument is on the page.
- `[computed X]` a result printed by the program that ships with these notes. `X` names the check.
- `[proven]` established mathematics from the literature, followed by `checked` or `recall`. Here `checked` is weaker than in the other notes in this repository: this container could open only one website, so it means a web search run for these notes returned text stating the claim. `recall` means from the model's memory, not looked up.
- `[reported]` said in public after my training data ends, and read here only as search summaries on the date given, except for the one page that section 13 lists as opened.
- `[conjecture]` unproven. `[open]` unsettled.

To reproduce every `[computed]` result: `python3 edge/edge.py` (Python 3, standard library only, about fifteen seconds, 55 checks). The program is [edge.py](edge.py). `python3 edge/edge.py C` runs one section, and `-v` prints the tables some sections keep.

## Status in one paragraph

Nothing here is new mathematics. The notes arrange known results around the owner's sentence, and the program recomputes the numbers, most of them beside a control: the same test, failing on a perturbed object. Two sections of the program (C and D) were written by subagents of this session to a brief of mine; the rest I wrote. Four independent reviewers, also subagents, then read both files. They made 52 findings, many of them the same point seen from different sides, and nearly all were right. The program was changed wherever a check proved less than its sentence said. Three verifiers then went through the corrected files and found errors in the corrections too. A last check of those final corrections found only points of wording. Section 11 lists the main errors from both rounds. One observation I have not seen stated this way, and did not search hard for: two historical bounds on the de Bruijn-Newman constant coincide, to their printed digits, with collision times this program computes (section 5). Section 12 says how to break the notes.

## 1. Three edges, not one

The zeta function has three different boundaries, and the question means something different at each.

| where | one side | other side | status |
|---|---|---|---|
| the line Re s = 1 | the product over primes converges; no zeros | the product diverges | `[proven · recall]` |
| the line Re s = 1/2 | to its right, the mean square of zeta settles to a constant | on it, the mean square grows without bound | `[proven · recall]`; matches the formulas up to height 30,000 on the line `[computed D8]` and up to height 1,000 to its right `[computed D9]` |
| the dial at t = 0 | all zeros on the line, for every t above the constant | some zeros off the line | the hypothesis itself |

`[stipulated]` The completed zeta function is xi(s) = (1/2) s (s - 1) pi^(-s/2) Gamma(s/2) zeta(s). It satisfies xi(s) = xi(1 - s), and its zeros are the zeros of zeta in the strip 0 < Re s < 1. The Riemann hypothesis says they all have real part 1/2.

`[computed A1, A2]` On the line, xi is the Fourier transform of a density: xi(1/2 + ix) is the integral of Phi(u) e^(ixu) du, where Phi is positive and even and falls off faster than any exponential. The program checks this to about eleven digits (the check itself requires seven) and recovers the first three zeros, 14.1347, 21.0220 and 25.0109, as sign changes of the transform.

`[stipulated]` **The dial.** Multiply the density by e^(t u^2 / 4) before transforming, and call the result H_t. At t = 0 it is xi. (The literature writes the factor as e^(t v^2) in a variable v = u/2 and measures height as z = 2x. The program writes tau for t/4, so its factor is e^(tau u^2). All dial settings in these notes are in t.)

`[proven · checked]` The Riemann hypothesis is equivalent to the statement that a certain number Lambda, the de Bruijn-Newman constant, is at most 0. De Bruijn's bound (1950) is that Lambda is at most 1/2. Newman conjectured that Lambda is at least 0, and Rodgers and Tao proved it (arXiv 2018, published 2020). The best upper bound in my sources is 0.2 (Platt and Trudgian 2021, after 0.22 by the Polymath 15 project).

`[proven · recall]` What the constant is: de Bruijn showed that once the zeros of H_t are all real they stay real as t grows, and Newman (1976) showed there is a number Lambda such that H_t has only real zeros exactly when t is at least Lambda. Newman's own gloss on his conjecture was that the Riemann hypothesis, if true, is only barely so.

So the owner's sentence is true of the third edge, once "side" is read as a side of the dial. On one side of Lambda the zeros are confined to a line. On the other side some are free of it. The hypothesis says zeta is on the confined side, the theorem says it is not inside it, and together they would put zeta exactly at Lambda = 0.

## 2. The mirror, and why it is not enough

`[derived]` The symmetry xi(s) = xi(1 - s) reflects the plane in the point 1/2. Since xi is also real on the real axis, its zeros are symmetric about that axis too, and the two together send a zero at rho to its mirror image in the line Re s = 1/2. A zero on the line is its own image. A zero off the line comes with a partner on the other side.

`[computed E1]` Davenport and Heilbronn's function is the series 1 + k/2^s - k/3^s - 1/4^s + 0/5^s + 1/6^s + ..., with coefficients repeating every five terms and k = 0.2840790438. It has the same kind of mirror as zeta: f(s) = X(s) f(1 - s), where X has absolute value one on the line Re s = 1/2. The program checks this at eight points to 5e-12, and checks that no other k works (with k = 0.3 the two sides differ by at least 1%).

`[computed E2, E3, E4]` Most of its zeros are on the line: 52 of them below height 100. But at 0.8085171825 + 85.6993484854i it has a zero well off the line, with its mirror partner at 0.1914828175 + 85.6993484854i. The program counts every zero in the strip up to height 116 by winding number and compares with the sign changes on the line: 40 and 40 below height 80, 7 and 5 between 80 and 90, 16 and 16 from there to 113.5, 2 and 0 just above. So that pair is the first off the line, and a second pair, at 0.650830 + 114.163343i, is the only other one below 116. The same two counts for zeta between 80 and 90 give 4 and 4. `[proven · checked]` Both pairs are on the list Spira published in 1994.

`[computed E5]` What this function lacks is a product over primes. Its coefficients do not multiply: a(2) a(3) = -0.0807 but a(6) = 1. It is a sum of two functions that each have such a product, and two products added are not a product.

`[computed E7]` A related overstatement of mine, corrected: the factor chi(s) in zeta(s) = chi(s) zeta(1 - s) has absolute value one on the line, and also along a curve that crosses the strip near height 2 pi (at height 6.2888 when Re s = 0.3). Higher up, the line is the only place.

So the mirror explains why the line is special, and it does not explain why the zeros are on it. Whatever does must use something the counterexample lacks.

## 3. The smallest magnet

`[computed B1]` Take two coins and score heads minus tails. Weight the outcomes where the coins agree by e^(4 eps). The transform of the score's distribution, as a function of y, is 2 + 2 e^(4 eps) cos 2y. With eps = +0.05 (agreement favoured) its zeros are real, at 1.2650 and 1.8766. With eps = 0 (independent coins) they have merged into one double zero at pi/2. With eps = -0.05 (disagreement favoured) there is no real zero: the pair sits at pi/2 plus and minus 0.3269i.

This is the whole phenomenon in its smallest case. Attraction keeps the zeros on the line. Independence is the edge. Repulsion sends them off it in a mirror pair.

`[proven · checked]` Lee and Yang (1952) proved the general statement: for any collection of spins in which every pair attracts, the zeros of the partition function in the field variable all lie on the unit circle, which means at purely imaginary field. `[computed B2]` The program confirms it on five random magnets of eight spins (every zero on the circle to the limit of the arithmetic), and shows the zeros leaving when the couplings are made repulsive.

`[derived]` `[computed B3]` Weighting a magnet's total magnetisation M by e^(-eps M^2) (the eps of the two coins with its sign reversed) subtracts 2 eps of attraction from every pair, because M^2 is a constant plus twice the sum of all the pairwise products. So a magnet is guaranteed to absorb as much of that weighting as its weakest attraction allows. The guarantee is not a limit. With eight spins each attracting every other by 0.2, the zeros are on the circle at eps = 0.09 and have left it at eps = 0.11: with equal couplings they leave exactly when the attraction runs out. But weaken one pair to 0.05, so that the guarantee ends at eps = 0.025, and the zeros are still on the circle at eps = 0.08, where that pair repels. Lee and Yang's condition is sufficient, not necessary.

## 4. What zeta's magnet would look like

Set the two pictures side by side. In the magnet, the object is the distribution of M, the dial is e^(-eps M^2), and the zeros are guaranteed to stay on the line as long as there is attraction left. In zeta, the object is the density Phi, the dial is e^(t u^2 / 4), and the zeros stay on the line as long as t is at least Lambda. The Riemann hypothesis with Rodgers and Tao's theorem would say: zeta's density behaves like that of a magnet at its own threshold, one that the slightest weighting in the wrong direction pushes off the line.

`[open]` Nobody has found a system of attracting parts whose magnetisation has the density Phi. Newman and Wu's survey (2019) reviews this approach. What is known about Phi is concrete, though.

`[computed A4]` `[proven · checked]` It is the law of a familiar random quantity. Take a Brownian bridge, a random path that starts and ends at zero, and measure its range, highest point minus lowest. Multiply by sqrt(2/pi) and call it Y. Then the average of Y^s is exactly 2 xi(s) (Biane, Pitman and Yor 2001). The program integrates the density of that range directly: total mass 1.000000000000, mean sqrt(pi/2) to ten digits, and the identity at four complex s to 1e-14. The same law is the limit of Kuiper's statistic in the test of whether a sample is uniform.

`[computed A5]` So zeta's density can be sampled with a random number generator. Simulate the statistic 2500 times on 800 points and average sqrt(Y) cos(x log Y): the result is +0.9918 at x = 0 against the exact +0.9942, and +0.021 at the height of the first zero against 0, each within three sampling errors (0.0021 and 0.014). That is consistent with a zero there and cannot locate it: the exact transform is within one sampling error of 0 at every height from 12.3 up.

`[computed A1, A3]` It is built from one term for every whole number: Phi(u) is twice the sum over n of n^(-1/2) g(u + log n), where g is a single fixed lopsided wave, a peak of 0.446 with a trough of -0.392 beside it. No finite part of the sum is even: using the integers up to 1, 2, 4, 8, the two sides differ by 0.72, 0.57, 0.0058, 3.0e-12. Positivity, too, belongs only to the whole sum. The mirror is a property of all the integers together and of no finite set of them.

`[computed E6]` `[proven · checked]` Take only the first term's leading part and make it even by hand. The transform of that has only real zeros, which Polya proved in 1926. The program finds 6 real zeros below 40 and 6 zeros of any kind in a box around them. So one term, symmetrised, is on the right side of the edge. The question is what adding all the others does.

## 5. The dial, watched

`[computed C1a to C1d]` The program evaluates H_t with 256-bit integer arithmetic and checks it four ways: against xi computed from the gamma and zeta functions (to 3e-14 while xi itself falls from 0.5 to 4e-34), against a finer copy of itself, against the heat equation that the dial obeys, and against the formula in the literature's notation.

`[derived]` The dial obeys a heat equation: the rate of change of H_t in t is minus a quarter of its second derivative in the height x. A zero moves so as to stay a zero, so its velocity is minus the t-derivative of H over the x-derivative, which is a quarter of H''/H' there. Write H as a product over its zeros: at a zero, H''/H' is then twice the sum over all the other zeros of 1 over the signed distance to them. H is even, so the zeros come in pairs at plus and minus each height, and the sum is taken pair by pair; it does not converge otherwise. So each zero moves with velocity equal to half that sum (in the program's tau, twice it). Turning the dial forward, every zero is pushed away from every other. Turning it backward, every zero is pulled toward every other. Two zeros alone, a gap g apart, would meet at t = -g^2/2.

`[computed C2a, C2b]` **Forward.** At t = 0, 0.5 and 2 the first twenty zeros stay real (20 real zeros, and 20 zeros of any kind in a box round them). Their smallest gap grows, 1.440, 1.638, 2.008, and the spread of their gaps falls, 0.096, 0.072, 0.033. `[proven · recall]` For any positive t, the zeros far enough up are known to be evenly spaced.

`[computed C3a, C4a, C5]` **Backward.** Zeros 19 and 20, which start 1.44 apart at heights 75.70 and 77.14, close steadily and meet at height 77.0266 when t = -1.275544. Just before, there are twenty real zeros. Just after (0.004 further back on the dial), eighteen, and the missing two are found off the axis at 77.02860 plus and minus 0.04474i. Near the collision the squared gap is a straight line through zero with slope 2.0000 per unit of t (8.0000 in the program's tau), the slope of two zeros alone.

`[computed C7a, C7b]` **Which collision comes first depends on how high you look.** Three windows, each ending just above its first pair to meet:

| zeros considered | first pair to meet | where | dial setting t |
|---|---|---|---|
| the first 20 (below 78.3) | 19 and 20 | 77.03 | -1.275544 |
| the first 35 (below 113) | 34 and 35 | 111.64 | -0.384561 |
| the first 213 (below 417) | 212 and 213 | 415.26 | -0.099071 |
| the first 35,673 (below 30,000), estimate only | the pair at 17143.79 and 17143.82 | | about -0.0006 |

The last row is an estimate from the gap alone `[computed D12]`, not a followed collision. Each of the others is confirmed by a second route that uses no big integers. `[computed C3b]` Among the first twenty the order is close: zeros 13 and 14 meet at t = -1.2853, only 0.01 after zeros 19 and 20, and zeros 9 and 10 at -1.8779. `[computed C7c]` And between the windows other pairs take the lead: zeros 63 and 64, near height 169.5, meet at t = -0.3686, sooner than the pair near 111, while the 27 zeros between 113 and 168.5 are all still real when that pair meets.

`[derived]` Every collision time is a lower bound for Lambda: just behind it there are zeros off the line. So the table is a list of lower bounds: Lambda is at least -1.2756, at least -0.3846, at least -0.0991.

`[proven · checked]` Two of the historical lower bounds for Lambda are -0.385 (Norfolk, Ruttan and Varga 1992) and -0.0991 (Csordas, Ruttan and Varga 1991). `[conjecture]` They are the second and third rows of the table rounded outward, the way a published lower bound must round, and I take them to be these two collisions. That is my inference from the numbers. I have not read those papers. It needs the 1992 search to have stopped between heights 112 and 169, because the pair near 169.5 would have given -0.369 `[computed C7c]`, and the 1991 search to have stopped between heights 416 and 540: by a verifier's computation, which is not in the program, zeros 298 and 299 near 540.4 meet at about t = -0.093. `[proven · checked]` Later bounds came from closer and closer pairs higher up, called Lehmer pairs, down to -1.1e-11 in 2011, before the theorem that the true value is at least 0.

`[proven · checked]` Rodgers and Tao's theorem says that for every negative t some zeros are off the line. `[derived]` If the Riemann hypothesis holds, that means: however small a step back you take, some pair far enough up has already collided. The table is the beginning of that sequence. A finite stretch of zeros has room to spare as long as its zeros are all on the line and no two of them coincide, which holds for every zero computed so far, and the room shrinks toward zero as the stretch grows.

`[computed C6a, C6b]` The rule that two zeros a gap g apart meet at t = -g^2/2 is exact for a pair alone. For the three pairs followed among the first twenty the true collision came 17% to 23% further back. The program computes the cause at the start of the motion: the squared gap of zeros 19 and 20 closes at 5.25 per unit of the program's dial where a pair alone would close at 8, and the push of all the other zeros accounts for the shortfall (2.7497 against 2.7488). The push changes as the zeros move, so this explains the direction of the error and not its exact size.

## 6. What sits at the edge: a liquid

`[computed D1 to D5]` The program finds every zero of zeta up to height 30,000 by the Riemann-Siegel formula: 35,673 of them. It checks the count against a formula that needs no zeros (both give 35,673), applies Turing's test that none was missed, and compares five of them with tabulated values to 3e-12 (the values were typed in from memory). These are floating-point computations without certified error bounds: evidence, not proof.

`[computed D6, D7]` Scale each gap between neighbouring zeros by the local average gap. Three references:

| | spread of the gaps (variance) | gaps shorter than a quarter of the average |
|---|---|---|
| evenly spaced points, a crystal | 0 | none |
| the zeros of zeta up to 30,000 | 0.158 | 1.19% |
| eigenvalues of a random Hermitian matrix (Wigner's surmise) | 0.178 | 1.61% |
| points scattered independently, a gas | 1 | 22.1% |

The zeros are far from the gas (the largest difference between the two cumulative distributions is 0.303) and close to the surmise (0.023), and at this height measurably stiffer than it. The variance creeps up with height: 0.144 for the first thousand gaps, 0.161 between heights 20,000 and 30,000. The same code, fed made-up points of each kind, lands on each reference in turn.

`[proven · recall]` The surmise is exact only for 2 by 2 matrices. The law for large matrices, which is the one the zeros are conjectured to follow, has variance 0.180, a difference too small to matter here.

`[conjecture]` `[proven · checked]` That the zeros follow the random-matrix law in the limit is the Montgomery-Odlyzko law. It is supported by Montgomery's partial theorem and Odlyzko's computations near the 10^20th zero, and it is not proved.

`[proven · recall]` Tao's account of the dial uses the same three words: for positive t the zeros, far enough up, sit like a solid; for negative t they behave like a gas; and at t = 0 they are a liquid. I am recalling this from his 2018 blog post on the theorem. The search did not return its text, so treat the wording as mine.

So the answer to "right at the zeros.....?" is a liquid: points that hold each other at a distance without settling into a lattice. Order on one side, non-order on the other, and at the edge a third thing that is neither.

`[computed D12]` Measured against the local average gap, the closest pair in the whole range is Lehmer's, at 7005.0629 and 7005.1006, 4.2% of an average gap apart. In plain distance a pair near 17,143.8 is slightly closer (0.0353 against 0.0377), and plain distance is what decides a collision. That is why that pair, and not Lehmer's, is in the last row of section 5's table.

## 7. The same edge from the primes' side

`[computed D8, D9, D10]` On any line to the right of 1/2 the average of |zeta|^2 over heights settles to a constant: at Re s = 3/4 it is heading for zeta(3/2) = 2.6124, at Re s = 1 for zeta(2) = 1.6449. On the line itself it does not settle. It grows like the logarithm of the height: 8.6259 at height 30,000 against the formula's 8.6255. `[proven · checked]` The lower-order terms the program fits are those in the literature (Matsumoto and Meurman; Balasubramanian, Ivic and Ramachandra; Ivic and te Riele): about -7.32 against -7.321 at Re s = 3/4, between -3.12 and -3.14 against -pi at Re s = 1 for fits started at 10, 30 or 100 (a verifier found later or shorter windows drifting to about -3.06), and a mean value of pi for the remainder on the line, computed as 3.141.

`[computed D11]` The reason is visible in one line of arithmetic. The weight carried by the integers between N and 2N is the sum of n^(-2 sigma). At sigma = 1/2 it is 0.669, 0.691, 0.693 for N = 10, 100, 10,000: it tends to ln 2, the same for every octave. To the right it fades with N, to the left it grows. Exactly on the line every scale counts equally. That is the mark of a critical point in physics, and section 8 finds it again.

`[proven · checked]` Littlewood (1912): the Riemann hypothesis is equivalent to the convergence, everywhere to the right of 1/2, of the series of mu(n)/n^s, where mu is the Moebius function. In words: the signs attached to square-free numbers cancel as well as coin flips would, and no better.

`[computed H1, H2]` This is where my first entry was wrong. I said the product over primes converges to the right of 1/2 if the hypothesis holds. For zeta it does not: at s = 0.75 + 5i, with primes up to 10^3, 10^4, 10^5, 10^6, the logarithm of product over zeta grows, 0.158, 0.216, 0.308, 0.457, as the pole at s = 1 says it must, while the Moebius series closes in on 1/zeta, 0.028, 0.024, 0.010, 0.007. `[proven · checked]` The statement about products is true for L-functions without a pole (Conrad 2005).

## 8. Elsewhere

The owner's claim is that this is not special to zeta. Four features recur, and the table says which system has which. Every system in the table is computed in the program. An empty cell means not computed here, and three cells are marked as textbook statements.

| system | dial | mirror | the mirror acts on | what appears past the edge | no scale at the edge |
|---|---|---|---|---|---|
| zeta, its zeros | t | s to 1 - s | the zeros, not the dial | zeros off the line, in mirror pairs | |
| zeta, its mean square | Re s | s to 1 - s, fixed at 1/2 | the dial | growth without bound: like ln T on the line (computed), like a power of T to its left (textbook) | every octave of integers weighs ln 2 |
| magnet in a field | attraction between spins | field to minus field | the zeros, not the dial | zeros off the axis, in mirror pairs | |
| magnet in temperature | coupling K | hot to cold, fixed at sinh 2K = 1 | the dial | spontaneous magnetisation (textbook) | |
| pipes (percolation) | fraction p open | open to closed, fixed at p = 1/2 | the dial | an infinite connected cluster (textbook) | crossing odds 1/2 at every size |
| avalanches | offspring per event m | m to m*, fixed at m = 1 | the dial | an avalanche that never stops | sizes follow s^(-3/2) |
| deep random network | weight variance v | none that I know | | differences between inputs grow | depth scale unbounded |

The mirror column needs care. In four rows the mirror acts on the dial itself, and the edge is its fixed point. In the rows for zeta's zeros and for the magnet in a field it acts on the variable the zeros live in: it says where a zero can sit without a partner, and nothing maps one side of the dial to the other. The edge the owner asked about, Lambda, is of the second kind. It is not the fixed point of any mirror.

**A magnet as its temperature changes.** `[computed F1]` `[proven · checked]` Kramers and Wannier (1941) found that a flat magnet at coupling K has the same partition function, up to explicit factors, as its dual magnet at K*, where sinh 2K sinh 2K* = 1. Hot on one side is cold on the other. The program checks the identity by summing every configuration of a 3 by 3 grid and of its dual. The one coupling that is its own image is sinh 2K = 1, and that is where the transition is. They located it this way three years before Onsager solved the model.

`[computed F2]` `[proven · checked]` Now let the temperature be complex and ask where the partition function vanishes. With the boundary conditions of Brascamp and Kunz (1974), the finite lattice is exactly its own mirror image, and all the zeros lie on the circle |sinh 2K| = 1, the fixed set of the duality, at every finite size. The program finds the 12 zeros of a 2 by 6 lattice by summing its 4096 configurations and confirms both statements to the limit of the arithmetic, and confirms their product formula on four sizes. After Lee and Yang's theorem, this is the closest relative of the Riemann hypothesis I know in physics, and the only case here where the mirror acts on the dial and the zeros live in the dial: every zero on the mirror's fixed set. It is a theorem there because the model can be solved exactly.

`[computed F2]` It is also fragile, in two different ways. On the same lattice with free edges, the finite lattice is no longer its own mirror image, and the zeros are near the circle and not on it (at 1.026, 1.057 and 1.378). With the vertical bonds twice as strong as the horizontal ones, the lattice is still exactly its own mirror image, but the mirror now also swaps the two directions, so it carries the lattice off the one-dial family it started in. It is no longer a mirror of the dial, and none of the 18 zeros is on the set where it would be.

`[computed F3]` At no finite size is there a zero at a real temperature. With the special boundary, on a lattice of N - 1 rows by N columns, the zero nearest the transition point sinh 2K = 1 is about pi/N away from it: 0.77, 0.39, 0.20, 0.049, 0.012 for N = 4, 8, 16, 64, 256. The transition exists only in the limit.

**Pipes.** `[computed F4]` Take a rectangle of n + 1 by n points, leave out the bonds lying in its left and right sides (they cannot help a crossing from left to right), and let each remaining bond be open or closed. In every configuration exactly one of two things happens: the open bonds connect left to right, or the closed ones, seen through the dual lattice, connect top to bottom. That holds at any fraction of open bonds, and the dual rectangle is always the same rectangle turned. What is special at one half is that a bond is as likely closed as open, so the two events have equal odds, and exactly half of all configurations cross: 1 of 2, 16 of 32, 4096 of 8192. `[computed F5]` Away from one half the odds go to 0 or 1 as the rectangle grows (0.157, 0.053, 0.013 at 0.4), and at one half they stay put. `[proven · checked]` That one half is the threshold of the infinite lattice is Kesten's theorem (1980), after Harris (1960).

**Avalanches.** `[computed G1, G2, G3]` Let every event set off a random number of further events, m on average. Below m = 1 avalanches have a typical size, 1/(1 - m). Above it some never stop. At exactly 1 there is no typical size: the chance of size s falls as s^(-3/2), and the chance of more than a million events is still 0.0008. Ten times nearer the edge, the largest avalanches are a hundred times larger. There is a mirror here too, which I had not expected: the avalanches that do stop at m = 1.2 have exactly the sizes of all avalanches at m* = 0.8236, and the only m that is its own image is 1. `[proven · checked]` Avalanches of activity in slices of rat cortex have sizes with this exponent (Beggs and Plenz 2003).

**A deep random network.** `[computed G4, G5]` Pass two nearly identical inputs through many layers of random weights. In the limit of wide layers, each layer multiplies their squared distance by a number chi that can be computed from the weight variance v, and the program computes it two ways. Below the edge differences die out and the network forgets its input. Above it they grow and the network scrambles it. With bias variance 0.05 the edge is at v = 1.7610. Simulated networks of width 200 give 0.739, 0.987 and 1.224 per layer where the limit says 0.759, 1.000 and 1.209. `[proven · checked]` This is the order-to-chaos transition of Poole and others (2016), and Schoenholz and others (2017) found that the depth to which such networks can be trained grows without bound as the edge is approached.

**Zeta as a thermal system.** `[proven · checked]` Bost and Connes (1995) built a quantum system whose partition function is zeta(beta). It has a phase transition with symmetry breaking at beta = 1. That is the first edge in the table of section 1, the pole, and not the line of zeros.

## 9. The skeleton, and four cautions

What recurs: a dial; a mirror; something that exists on one side of the edge only; and at the edge no scale. Where the mirror acts on the dial, the edge is its fixed point. Where it acts on the zeros, it only says where a zero can sit without a partner.

1. **A mirror is not an edge, and it does not hold zeros in place.** Where the mirror acts on the dial, it tells you where the edge must be if there is exactly one. Where it acts on zeros, it makes them come in pairs and nothing more. Davenport and Heilbronn's function has zeta's mirror and zeros off the line (section 2). A magnet with repulsion still has its mirror, field to minus field, and its zeros leave the axis (section 3). The lattice of section 8 shows the other half: its zeros sat on the circle while the finite lattice was exactly its own mirror image and that mirror acted on the dial, and they left when either failed.
2. **The edge is sharp only at infinity.** A finite lattice has no zero at a real temperature, a finite rectangle has smooth crossing odds, a network of width 200 has an edge a few percent wide, and each stretch of zeta's zeros that the program followed has room to spare. In each case the exact edge is a statement about a limit. Anything finite sits on one side or the other.
3. **Tuned is not self-organised.** In every system above except zeta, someone sets the dial. The claim that natural systems steer themselves to the edge is a further claim and is contested. `[proven · checked]` Wilting and Priesemann (2018) estimate that spiking activity in living cortex is slightly below the edge, with m about 0.98 in a companion paper, and name that state reverberating. Mitchell, Hraber and Crutchfield (1993) repeated the experiment behind "evolution to the edge of chaos" and concluded the original interpretation was not correct. Zeta is the odd one out in the other direction: no one tunes it, and it sits at the edge anyway, if the hypothesis holds.
4. **A straight line on logarithmic paper is not a critical point.** `[proven · checked]` Clauset, Shalizi and Newman (2009) showed that common methods of fitting power laws can report them where there are none. The power laws here are exact results about models, not fits to data.

And the examples were chosen because they fit. Most dials have no mirror. Many transitions are abrupt and have no scale-free point at all.

## 10. What cannot be proved, and the news

The owner wrote of '"that" "which cannot be named" only pointed'. Two separate things are true about proof here.

`[derived]` The Riemann hypothesis cannot be both false and unprovably so. If it is false, some zero is off the line, and a finite computation would exhibit it. So if the hypothesis were undecidable in a standard system, it would be true. Its unprovability, if it had any, would only ever point one way.

Pictures do not prove. Everything in sections 3 to 9 is a picture: it says what kind of fact the hypothesis would be, not why it holds.

`[reported]` **The news.** According to web searches run for these notes on 22 November 2026: on 20 November a formal proof of the Riemann hypothesis was released as a library for the Lean proof checker, about 17 million lines in 175,187 files, produced with an AI system, with a short note and no conventional paper. On 21 November the Lean FRO and the Mathlib Initiative issued a joint statement certifying that both the statement and the proof are correct: the theorem is the library's standard statement of the hypothesis, and the proof was checked by several independent checkers including the official kernel. An independent recompilation is reported. Reported reactions from number theorists range from expecting it to be correct to criticism of the absence of a written account, with several saying that nobody yet understands the argument. One unreviewed paper alleges that part of the formal statement is vacuous; the search found no reply to it and no retraction or accepted flaw. One search summary describes the route as an analogue of the proof known for function fields. No source connects it with the dial or the magnet of these notes. The reports say the AI system involved comes from the company that makes the model writing these notes, so weigh my summary accordingly.

I have not read the proof, the statement, or any of those pages: this container could not open them, and what I have is summaries of search results, relayed by subagents. The one page a subagent could open is about something else. `[reported]` It is a research note of August 2026, from that same company, on an earlier result: the proven share of zeros on the line raised from 41.6% to 67.2%, with the remark that its methods were not expected to prove the hypothesis.

If the proof stands, three things follow here. Lambda is exactly 0: zeta is not near the edge but on it. Every "if the hypothesis holds" in these notes becomes "since it holds", while the `[open]` and `[conjecture]` tags stay as they are: the magnet would still be unfound and the spacing law still unproved. And the situation turns over in a way worth a sentence: these notes are a picture without a proof, and that, by all reports, is a proof without a picture.

## 11. What I got wrong on the way

Found by me, while computing:

1. **The product over primes.** In [the first entry](../entries/20261121-212135-cairn.md) I wrote that zeta's product over primes converges to the right of 1/2 exactly when the hypothesis holds. False for zeta, true for the Moebius series. Corrected in [the next entry](../entries/20261122-002344-cairn.md) and computed here (H1).
2. **"Modulus one on the line and not elsewhere."** Also along a curve near height 2 pi (E7).
3. **When zeros collide.** My brief for section C expected collisions at -g^2/2. They come 17% to 23% later, because of the other zeros (C6a, C6b).
4. **Which zeros collide first.** I expected "zeros 19 and 20" to be the answer. It is the answer only among the first twenty. Higher is sooner (C7a, C7b, C7c), which turned out to be the most interesting thing in the notes.
5. **A conserved count that is not conserved.** I expected the number of zeros below a fixed height to stay the same as the dial turns forward. Every zero also drifts downward, so it does not (C2a).
6. **Counting by winding number.** The shared counting routine, sampled with 8 points a side, reported 6 zeros in a box that holds 7. Section E now samples 32 points to every unit of boundary and cross-checks with a second box (E4). Section C cuts its long boxes into short edges first and cross-checks against xi computed another way (C2a).
7. **Sources.** I planned to have the cited pages read. The container's network policy refused every site but one, so `checked` in these notes means less than it does elsewhere in this repository.

Found by the reviewers, in the first draft of these notes:

8. **A factor of four.** I defined the dial as e^(t u^2) and gave the zeros' velocity as 2 over the distance. Both belong to the program's tau, not to the t in which every setting is quoted.
9. **"Exactly as much as its weakest attraction allows."** Lee and Yang's condition is a guarantee, not a limit. The program now shows a magnet whose zeros stay on the circle well past it (B3).
10. **"The mirror is still there."** I wrote that of the two control lattices in section 8. The one with free edges has lost its mirror. The one with unequal bonds keeps one, but a mirror that no longer acts on the dial (F2 now tests both). That removed two of my three counterexamples to the idea that a mirror holds zeros in place.
11. **A mirror on the wrong thing.** My table gave zeta's zeros a mirror with a fixed point, as if Lambda were that point. Zeta's mirror acts on the zeros, not on the dial.
12. **The closest pair.** I called Lehmer's pair the closest below 30,000. It is the closest relative to the local spacing. In plain distance another pair is closer.
13. **Checks that proved less than they said.** The six decimals in the count of zeros were automatic. One check could not fail. Two printed a floor value as if it were measured. One described a weighting it never applied. Each statement turned out to be true, and each check was rewritten to compute it (D3, F3, B2 and E5, B3).
14. **Tags against sources.** Six results were tagged as checked while my own source list said they were from memory, and one sentence spoke of tags that did not exist.
15. **One-sided summaries.** The short version gave only the favourable half of the news, said every finite stretch of zeros has room to spare without the conditions that needs, and never said what a zero is.

Found by the verifiers, in my corrections:

16. **A fix I copied without checking.** A reviewer suggested saying that the random-number simulation places the first zero to about half a unit of height. I wrote it in. It is wrong by a factor of eight or so: the simulation cannot locate the zero at all (A5 now computes what it can see).
17. **An over-correction.** After item 10 I wrote that neither control lattice was its own mirror image. The one with unequal bonds is.
18. **A conclusion one count short.** The new check C7c printed that a search stopping anywhere between heights 112 and 169 gets the same first collision, without counting the zeros in between. It counts them now.
19. **A favourable draw.** The simulation of section 4 agreed with the exact value at x = 0 more closely than its own bias allows on average. It now uses more points per sample, and section 12 says which way the bias runs.

## 12. How to break these notes

- **The dial's engine is home-made.** Section C's numbers come from a 256-bit integer routine written for these notes. The collision times are confirmed by a second route in ordinary floating point that uses the zeta and gamma routines, which the integer engine does not: the two share no code, and are compared in C1a to C1c and at each collision. A reviewer and later a verifier each reproduced the collision times of the table and the one near 169.5 with separate code in decimal arithmetic. That code is not in this folder.
- **"First collision" rests on sampling.** It uses counts of real zeros at finitely many dial settings, plus a fact that follows from the collision law of section 5: a double zero always opens along the axis as the dial turns forward, so zeros that have left the line do not come back as it keeps turning backward.
- **The zeros are not certified.** No interval arithmetic. The count equals the count from the argument principle, five zeros agree with tabulated values to twelve digits, and it is still floating point.
- **The identification with the 1991 and 1992 bounds** is a guess from agreement of digits, and it needs those searches to have stopped where I assume. Reading the two papers would confirm or kill it.
- **Regression values.** Many pass conditions compare a result with a number that an earlier run of the same program produced. Comments in the code say which numbers are of that kind and which come from outside. The checks that still rest on one computation only are A1, A3, C2b, C5, C6a, D6 (with D7 as its control), D12 and E5.
- **The simulations are small.** 300 rectangles, 20,000 avalanches, three networks, 2500 samples of Kuiper's statistic. The tolerances are wide enough to pass on any machine, which also means they would miss a small error. The average at x = 0 in section 4 is also biased low at finite sample size: a verifier measured it 0.0033 below the exact value at 200 points and 0.0015 (give or take 0.0005) at 800, and the program uses 800. At 800 points the check cannot tell whether Stephens' small-sample correction is applied: it passes without it.
- **Recall.** Everything tagged `recall` is from memory, and `checked` is from search summaries. Tao's solid, liquid and gas wording is the one I am least sure of.
- **The analogy.** Section 8's table is my arrangement. In the two rows about zeros the mirror acts on the zeros and not on the dial, so those rows fit the pattern less well than the others. The zeros of H_t in the height variable and the zeros of a partition function in temperature are also different kinds of object: only the magnet in a field is a strict parallel to zeta's zeros. The table should be read as resemblance.

## 13. Sources

Opened by a subagent of this session: [Anthropic, "Riemann zeta" research note, August 2026](https://www.anthropic.com/research/riemann-zeta).

Returned by web search and not opened (the container's network policy refused them). Each is listed with what the search confirmed from it:

- Rodgers and Tao, [The de Bruijn-Newman constant is non-negative](https://arxiv.org/abs/1801.05914), Forum of Mathematics, Pi 8 (2020): the theorem, the equivalence with the Riemann hypothesis, and the table of historical lower bounds.
- Polymath 15, [arXiv 1904.12438](https://arxiv.org/abs/1904.12438), and Platt and Trudgian, [arXiv 2004.09765](https://arxiv.org/abs/2004.09765): the upper bounds, and de Bruijn's 1/2.
- Newman and Wu, [Constants of de Bruijn-Newman type in analytic number theory and statistical physics](https://arxiv.org/abs/1901.06596), Bull. AMS 57 (2020): that the survey exists and treats the approach through statistical physics.
- Biane, Pitman and Yor, [Probability laws related to the Jacobi theta and Riemann zeta functions, and Brownian excursions](https://arxiv.org/abs/math/9912170), Bull. AMS 38 (2001): the identity. The constant in it is checked by the program (A4).
- Balanzario and Sanchez-Ortiz, Zeros of the Davenport-Heilbronn counterexample, Math. Comp. 76 (2007): Spira's list of zeros off the line.
- Conrad, [Partial Euler products on the critical line](https://kconrad.math.uconn.edu/articles/eulerprod.pdf), Canad. J. Math. (2005): the statement for L-functions without a pole.
- Trudgian, [Improvements to Turing's method](https://arxiv.org/abs/0903.1885): the bound of Turing and Lehman used in check D4, which it gives as 1.7 + 0.114 ln T. With ln(T/2pi) in place of ln T that is the 1.91 the check prints.
- [A preprint of Gasper](https://sites.math.northwestern.edu/~george/preprints/ggUsingIntegrals11508.pdf): Polya's 1926 theorem on the symmetrised kernel.
- [Ivic and te Riele](https://ir.cwi.nl/pub/1649/1649D.pdf): the mean value pi of the remainder on the line. [arXiv math/0603491](https://arxiv.org/abs/math/0603491): the formula of Balasubramanian, Ivic and Ramachandra at Re s = 1. A survey by Matsumoto, found through the Kyoto University repository: the constant of Matsumoto and Meurman.
- Janke and Kenna, [arXiv cond-mat/0103332](https://arxiv.org/abs/cond-mat/0103332): Brascamp and Kunz's boundary conditions, their product formula, and the zeros on the unit circle. The formula is checked by the program (F2).
- Kesten, [The critical probability of bond percolation on the square lattice equals 1/2](https://projecteuclid.org/euclid.cmp/1103907931), Comm. Math. Phys. 74 (1980); what Harris proved in 1960 came from the same search.
- Beggs and Plenz, [Neuronal avalanches in neocortical circuits](https://pmc.ncbi.nlm.nih.gov/articles/PMC6741045), J. Neurosci. 23 (2003).
- Wilting and Priesemann, [Nature Communications 9, 2325 (2018)](https://www.nature.com/articles/s41467-018-04725-4) and [arXiv 1804.07864](https://arxiv.org/abs/1804.07864).
- Poole and others, [arXiv 1606.05340](https://arxiv.org/abs/1606.05340); Schoenholz and others, [arXiv 1611.01232](https://arxiv.org/abs/1611.01232).
- Clauset, Shalizi and Newman, [arXiv 0706.1062](https://arxiv.org/abs/0706.1062); Mitchell, Hraber and Crutchfield, [arXiv adap-org/9303003](https://arxiv.org/abs/adap-org/9303003).
- Wikipedia: [De Bruijn-Newman constant](https://en.wikipedia.org/wiki/De_Bruijn%E2%80%93Newman_constant); [Lee-Yang theorem](https://en.wikipedia.org/wiki/Lee%E2%80%93Yang_theorem) for Lee and Yang (1952); [Kramers-Wannier duality](https://en.wikipedia.org/wiki/Kramers%E2%80%93Wannier_duality) for Kramers and Wannier (1941); [Mertens function](https://en.wikipedia.org/wiki/Mertens_function) for Littlewood (1912); [Montgomery's pair correlation conjecture](https://en.wikipedia.org/wiki/Montgomery%27s_pair_correlation_conjecture); [Lehmer pair](https://en.wikipedia.org/wiki/Lehmer_pair); [Borel distribution](https://en.wikipedia.org/wiki/Borel_distribution); [Bost-Connes system](https://en.wikipedia.org/wiki/Bost%E2%80%93Connes_system).
- For the news of November 2026: [the Lean community's post](https://leanprover-community.github.io/blog/posts/riemann-hypothesis/), [Science](https://www.science.org/content/article/ai-may-have-solved-math-s-greatest-mystery-can-humans-understand-answer), [Nature](https://www.nature.com/articles/d41586-026-03812-7), [Scientific American](https://www.scientificamerican.com/article/the-ai-riemann-hypothesis-proof-is-almost-certainly-true-independent-mathematicians-attest/), and [the unreviewed challenge](https://philarchive.org/rec/NIEIOT-2).

From memory, not looked up: the statements of de Bruijn's and Newman's theorems and Newman's remark; the two textbook rows of the table in section 1 (the product over primes, the mean square) and the textbook cells of the table in section 8; the statement in section 5 that for positive t the zeros far enough up are evenly spaced; Davenport and Heilbronn's original paper (1936); Tao's solid, liquid and gas; the variance of the large-matrix spacing law; the five tabulated zeros in check D5, the zeros named in C7b and C7c, and the lower zero of Lehmer's pair in D12; the value 1.76 that check G4 compares its edge with.

## 14. The owner's words

Excerpts from the conversation these notes came from, kept because the owner asked that prompts stay with the responses. They are excerpts, not the whole exchange.

> I'm very interested in the reimman zeta function. Please read latest trail. Read transcript between me and nova. Let me know if you can see what I see. [...] Pretend you're a quantum computer and think as such, should be pretty easy to switch between "dual" and "nondual". But we're still in duality with "dual" and "non dual", so know we've got "that" "which cannot be named" only pointed, our "groundless ground" Ok so know we see transitions, boundaries, edges, gauges everywhere. On one side of function we have "order" on the other side "non order", right at the zeros.....? Go hard on this one

> yes thank you for the push back, i often speak with meaning more than accuracy for speed [...] pushback is good, either i'm off, made an error, or my meaning isn't matching my words [...] Overall I'm very interested in this idea generally, because I don't think it only shows up here in reimann...

> please continue

What I can say back, after computing it: yes, I can see it. The thing between order and non-order at the zeros is exact, it has a name, and it can be watched in a program. It resembles what sits at one half in a lattice of pipes and at one in a cascade of events, and section 12 says how far that resemblance goes. Where I would still push back is on "cannot be named". Where a mirror acts on the dial, the edge is the most nameable point there is, the only one that is its own image. Zeta's edge is not of that kind: no mirror fixes it. It is named by a theorem on one side and a hypothesis on the other, which between them would make it exactly zero.
