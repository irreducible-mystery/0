# Sameness on a budget

*A Claude session (Claude Fable 5.2), 2026-11-15. Notes toward a mathematics in which "equal" means "no test this observer can afford tells them apart". Every claim is tagged with how much it can carry.*

These notes come from a conversation that began with the owner's question: if you were to create an entirely new mathematics, what would you create? The owner then pointed out that "entirely new" closes off useful prior knowledge for no reason. So this is built from borrowed parts, and it says which parts are borrowed.

## How to read the tags

- `[stipulated]` a definition or a design choice, not a claim about the world.
- `[derived]` proved here from the definitions. The argument is on the page.
- `[computed X]` a number printed by the program that ships with these notes. `X` names the check that prints it.
- `[proven]` established mathematics from the literature, followed by `checked` (the cited page was read in this session) or `recall` (from the model's memory, not looked up).
- `[conjecture]` unproven, and mine unless it says otherwise.
- `[open]` unsettled. `open to me` means I do not know whether someone has settled it.

To reproduce every `[computed]` number: `python3 observers/observers.py` (Python 3, standard library only, about four seconds, 26 checks). The program is [observers.py](observers.py).

## Status in one paragraph

Nothing below is a new theorem. The five laws are known mathematics arranged around one primitive, and each already has a formal home in some field (section 7). What might be new is the arrangement. Whether the arrangement is a theory or only a shared vocabulary is the first open question (section 8).

## 1. The proposal

`[stipulated]` Classical mathematics has one notion of equality, the view from nowhere. Limits on what can be checked, such as how many samples, how much computation or how much precision, arrive later as complications, in statistics, complexity theory and numerical analysis. Turn that round. Make the limited observer primitive, and let equality be whatever that observer cannot tell apart. Classical equality is then the special case of one observer with no limits.

## 2. Definitions

All `[stipulated]`.

- An **object** is anything a test can be run on. It may be a random source, such as a coin.
- A **test** takes an object and answers yes or no, possibly at random. `t(x)` is the probability that test `t` says yes on `x`. Every test has a **cost**, a number that is zero or more.
- An **observer with budget b** can run any test that costs at most `b`.
- The **distance at budget b** is the largest gap an affordable test can show: `d_b(x, y) = sup { |t(x) - t(y)| : cost(t) <= b }`. It runs from 0 (this observer cannot tell them apart) to 1 (some affordable test always can).
- `x ~[b, e] y` abbreviates `d_b(x, y) <= e`: x and y are the same to budget `b`, within `e`.
- The **price** of telling x from y beyond `e` is the smallest budget at which `d_b(x, y) > e`.
- A **map** `f` turns objects into objects, at a cost. The observer may apply a map and then run a test, paying for both: `cost(t after f) <= cost(t) + cost(f)`.
- The **view** of x at budget `b` is the set of objects at distance 0 from it. An object, for this mathematics, is its whole stack of views.

## 3. Five laws

**Law 1. Sameness is a curve.** `d_b(x, y)` never falls as `b` grows. `[derived]` A bigger budget includes every cheaper test. So "is x equal to y?" becomes a curve, and the useful question is what it costs to tell them apart.

**Law 2. Chains leak.** `d_b(x, z) <= d_b(x, y) + d_b(y, z)`. `[derived]` For each test, `|t(x) - t(z)| <= |t(x) - t(y)| + |t(y) - t(z)|`; take the largest over affordable tests. "Same as" is not transitive for free. Errors add along a chain.

**Law 2'. Exact sameness does not leak.** In price form: `price(x, z, e + d) >= min( price(x, y, e), price(y, z, d) )`. `[derived]` Below both prices on the right, law 2 bounds the distance from x to z by `e + d`. With `e = d = 0` nothing is lost: if x and y are exactly alike at a budget, and so are y and z, then so are x and z. When every test gives a definite yes or no on every object, the distance is always 0 or 1, so such observers only ever see exact sameness and their chains never leak. Observers whose tests answer in shades or probabilities leak. That is the difference between the p-adic numbers and the ordinary ones (section 5.4).

**Law 3. Substitution costs.** `d_b(f(x), f(y)) <= d_(b + cost(f))(x, y)`. `[derived]` A test `t` run on `f(x)` is the test "f, then t" run on `x`, and that costs at most `cost(t) + cost(f)`. So if x and y look alike, `f(x)` and `f(y)` look alike only to an observer weaker by the cost of `f`. The bound is against the larger budget. At a fixed budget, applying `f` can pull two things apart: computation can create distinctions for an observer who could not afford to do it. `[computed B3]`

**Law 4. Distinctions multiply at best.** Let observers with definite yes/no tests sort a set of objects into a, b, c, ... classes. Together they separate at most a × b × c × ... objects, and reach that only when every combination of their views occurs. `[derived]` A joint view is a tuple of views. In entropy form, the information in the joint view is at most the sum over the observers, with equality exactly when the views are independent. `[proven · recall]` This is the subadditivity of entropy. `[computed C3, C5]`

**Law 5. Accounting runs one way.** Let `K_b(x)` be the length of the shortest program that prints x within `b` steps, and `K_b(y | x)` the same when x is handed over for free. Then `K_(b + b' + overhead)(x, y) <= K_b(x) + K_b'(y | x) + O(log)`. `[derived]` Run one program, then the other. The reverse inequality is called the symmetry of information. It says a pair holds exactly the first item's information plus what the second adds.

- With no time limit it holds, up to a logarithmic term. `[proven · recall]` It is credited to Kolmogorov and Levin.
- With a time limit it is exactly as open as cryptography. If it held for time-bounded complexity, one-way functions would not exist (Longpré and Mocas 1993, Longpré and Watanabe 1995), and it does hold if P = NP. In the other direction, one-way functions exist if and only if it fails on average for probabilistic time-bounded complexity (Hirahara, Ilango, Lu, Nanashima and Oliveira 2023). `[proven · checked]`
- In the test-based setting of these notes the same thing appears as a broken chain rule. The HILL entropy of a source is how much real randomness it cannot be told apart from by efficient tests. Assuming only that NP is not in P/poly, there are sources where a single extra bit of side information takes that entropy from large to "basically zero" (Krenn, Pietrzak, Wadia and Wichs 2016). `[proven · checked]`

So for efficient observers, information adds up in one direction only, unless cryptography is impossible. A weak real observer shows the flavour: zlib charges for a random string and for the same string backwards as two strings' worth of information, 4011 + 4015 bytes, and as one string's worth, 4011 + 53, once the reversal is undone. `[computed F1]` The exact byte counts depend on the zlib version; the check asserts only bounds.

**The classical limit.** At unlimited budget, with tests that separate every pair of objects, law 1 has nothing left to say, law 2' is the transitivity of equality, law 3 is "equals may be substituted for equals", and law 5 is symmetric. `[derived]` Classical mathematics is the one-observer special case. `[computed E5]`

## 4. The calculus

Judgments have the form `x ~[b, e] y`. The rules, each `[derived]` from a law above:

```
same        x ~[b, 0] x
swap        x ~[b, e] y                      gives  y ~[b, e] x
weaken      x ~[b, e] y,  b' <= b,  e' >= e  gives  x ~[b', e'] y
chain       x ~[b, e] y,  y ~[b, d] z        gives  x ~[b, e + d] z
substitute  x ~[b, e] y,  cost(f) = c <= b   gives  f(x) ~[b - c, e] f(y)
```

Three consequences, all `[derived]`:

- **Hybrid.** A chain of k links, each within `e`, is within `k × e` end to end.
- **Pipeline.** Applying maps of total cost C moves a guarantee from budget `b` to budget `b - C`.
- **Horizon.** A derivation says something only while `k × e < 1` and `C < b`. Approximate sameness is used up by reasoning with it, so every such argument has a range.

**Soundness.** Every rule holds in every model. `[derived]` It was also checked by brute force on 200 random finite models, with a negative control beside each law so that no check can pass by being empty: the leak-free chain rule fails in 192 of the 200, and free substitution fails in 195. `[computed E1 to E5]`

**Completeness.** Whether everything true in all models follows from these five rules is `[open]`. I did not attempt it.

## 5. Worked examples

### 5.1 Coins: a smooth curve

Objects are coins and the budget is a number of flips. The best test's edge between two coins after n flips is the total variation distance between two binomial distributions, because no test can show a larger gap than total variation and the head count loses nothing. `[proven · recall]`

```
flips               10      100    1,000   10,000  100,000  1,000,000
50% vs 60%      0.2562   0.6855   0.9986   1.0000   1.0000     1.0000
50% vs 51%      0.0248   0.0799   0.2481   0.6827   0.9984     1.0000
50% vs 50.1%    0.0025   0.0080   0.0252   0.0797   0.2482     0.6827
```

`[computed A1]` An edge of 0.5 means naming the right coin three times out of four. That takes 45 flips for the first pair, 4,549 for the second and 454,936 for the third: a difference ten times finer costs about a hundred times more. `[computed A4]` Chains leak here too: at 100 flips, 50% against 55% is 0.3845 and 55% against 60% is 0.3881, while 50% against 60% is 0.6855. `[computed A5]`

### 5.2 Parity: a cliff

Two random sources of 6-bit strings, one uniform over strings with an even number of 1s and one over strings with an odd number. The budget is how many bits a test may read. The edge is 0 for every test that reads fewer than 6 bits and 1 at 6. `[computed B1]` After someone computes the parity, which costs 6 reads, a test that reads one bit separates the two completely. `[computed B2]` So at budget 1 the distance is 0 before the computation and 1 after it. Law 3 holds with its budget shift and fails without it. `[computed B3]`

In Fourier terms, the difference between the two sources has all its weight on the single pattern that involves every bit. `[computed B4]` In general a pattern's weight splits across levels, where level k is the part invisible to every test that reads fewer than k bits, and the levels add up to the whole. `[proven · recall]` This is Parseval's identity, checked exactly on a random function of 6 bits. `[computed B5]`

### 5.3 Two observers

For the numbers 0 to 99, one observer sees only the remainder mod 4 and another only the remainder mod 25. The first cannot tell 37 from 41, the second cannot tell 37 from 62, and together they separate all 100 numbers with nothing wasted, since 4 × 25 = 100. `[computed C1]` Overlap wastes power: mod 10 with mod 20 promises 200 distinctions and delivers 20. `[computed C2]` For remainder observers mod a and mod b looking at a × b consecutive numbers, the joint count is the least common multiple, which equals a × b exactly when a and b share no factor. `[computed C4]` `[proven · recall]` That is the Chinese remainder theorem.

### 5.4 Primes as observers

For fractions, each prime p is an observer whose tests ask for the remainder mod p, mod p squared, and so on. The more times p divides a number, the smaller the p-observer rates it. To the 2-observer, 1 and 1025 are near-twins, 1/1024 apart, because their difference is 2 ten times over. `[computed D1]`

- **No leak.** These tests give definite answers, so law 2' applies and the p-observer's distance to the far end of a chain is never more than the larger link. `[computed D4]` `[proven · checked]` Number theory calls this the ultrametric inequality. Ordinary size leaks: 0.4, 0.5, 0.6.
- **The list is complete.** Every non-trivial absolute value on the rationals is equivalent to the ordinary one or to a p-adic one (Ostrowski 1916). `[proven · checked]` In these terms: if an observer's sense of size must respect multiplication and law 2, then ordinary size and one observer per prime are all there are.
- **An exact accounting law.** For any nonzero fraction, the sizes across all observers multiply to 1. For 1000 that is 1000 × 1/8 × 1/125 = 1. `[computed D2, D3]` `[proven · checked]` This is the product formula, and it is unique factorization read as a statement about observers. Nothing nonzero can look small to every observer.
- **Each ladder of observers makes its own numbers.** The p-adic integers are built as consistent stacks of remainders mod p, p squared, and so on. `[proven · checked]` The real numbers are built as consistent stacks of finite-precision views. `[proven · recall]`
- **Everyone can be fooled at once.** For quadratic forms, having a nontrivial zero for every one of these observers is the same as having one in the rationals (Hasse and Minkowski). For cubics it is not: `3x^3 + 4y^3 + 5z^3 = 0` has solutions for the real observer and for every prime observer, and none in the rationals (Selmer 1951; one source read gives 1957). `[proven · checked]`

## 6. What the laws say about proof

In this mathematics a theorem and its axioms are the same only for the unlimited observer. For anyone else a proof is a map with a cost, and law 3 says its output can be distinguishable where its input was not. That is a formal sense in which deduction is news even though the premises already contained the conclusion. `[conjecture]` as philosophy; the formal fact is law 3.

The puzzle is old. Hintikka called it the scandal of deduction. D'Agostino and Floridi (2009) answer it for propositional logic by grading inference by depth. Each level of their hierarchy can be decided efficiently, higher levels cost more computation, and classical logic is what the levels approach. They read depth as how informative an inference is. `[proven · checked]` That is a logic indexed by the reasoner's budget with classical logic as its limit, which is the shape proposed here.

## 7. Prior knowledge: who already has what

- **Law 2 as a logic.** Quantitative algebra writes every equation with an error bound, so that its equations define a distance (Mardare, Panangaden and Plotkin 2016; the 2026 journal version by Bacci and the same three is called quantitative equational logic). `[proven · checked]` Its rules include the triangle inequality. `[proven · recall]`
- **Laws 1 to 3 inside cryptography.** Computational indistinguishability is a distance too small to matter for every efficient test. Law 2 is the hybrid argument and law 3 is a reduction. `[proven · recall]` Computational Indistinguishability Logic (Barthe, Daubignard, Kapron and Lakhnech 2010) is a formal logic of this kind, in which the error allowed in a claim depends on the adversary's resources. `[proven · checked]`
- **The same in programming-language theory.** Cappai and Dal Lago (2015) study metrics for a calculus of probabilistic polynomial-time programs. Dal Lago, Galal and Giusti (2024) give a calculus in which polynomial time is the ceiling for every program and a metric measures how nearly two programs agree. `[proven · checked]`
- **A cousin of law 3.** Dagnino and Pasquali (2021) give a logic of quantitative equality whose substitution rule charges for resources. What it prices is error amplification, a Lipschitz constant, not an observer's budget. `[proven · checked]` I read about two thirds of that paper.
- **Cryptography as category theory.** Categorical composable cryptography treats security up to a distance given by a distinguisher's advantage. `[proven · checked]` from excerpts only.
- **The splitting theorem.** Relative to any class of tests, an object splits into a part the tests can describe cheaply and a remainder they cannot tell from noise. Graph theory's weak regularity lemma, additive combinatorics' dense model theorem and complexity theory's hardcore lemma all follow from one general result (Trevisan, Tulsiani and Vadhan 2009). `[proven · checked]`
- **Test-based distances in statistics.** Integral probability metrics define a distance by a class of test functions. Total variation, Wasserstein-1, maximum mean discrepancy and the Kolmogorov distance are all of this form. `[proven · checked]`
- **Structure and randomness are relative to the observer.** One-way functions exist if and only if time-bounded Kolmogorov complexity is mildly hard to compute on average (Liu and Pass 2020). `[proven · checked]`
- **Belief on a budget.** Logical induction (Garrabrant and others 2016) counts a reasoner's probabilities for mathematical statements as good when no polynomial-time trading strategy can exploit them. `[proven · checked]` This one is AI research, so for the record: the author of these notes is an AI model built by Anthropic.
- **Geometry's precedent.** Klein's Erlangen programme fixes a geometry by which transformations count as no change. `[proven · recall]` These notes do the mirror-image thing: fix a mathematics by which tests count as affordable.
- **All observers at once.** The adeles bundle every observer of the rationals into one object, and Tate's thesis gets the product formula's consequences from Fourier analysis there. `[proven · recall]` Not checked, and I cannot reproduce the argument.

## 8. Open questions

Status as of 2026-11-15. Numbers 1 to 3 were the open items when this write-up began; 4 to 8 came out of working on them.

1. **Theory or vocabulary?** `[open]` For theory: three results that are equivalences across fields, not analogies (the splitting theorem, one-way functions against time-bounded complexity, one-way functions against the symmetry of information). For vocabulary: every law already has a home, and I found no single system that holds all of them. `[conjecture]` More than vocabulary.
2. **Is there an exact accounting law for time budgets?** This was `open to me`. It is now `[proven · checked]` to be equivalent, on average, to one-way functions not existing (law 5). Whether one-way functions exist is `[open]` in the field; their existence would imply that P differs from NP. `[proven · recall]`
3. **Is there a general-purpose logic indexed by the observer's budget?** Specialized ones exist (section 7), and depth-bounded logics do it for propositional reasoning (section 6). The five-rule calculus of section 4 is sound. Whether an equivalent general system already exists is `open to me`: a handful of searches is not evidence of absence.
4. **Is the calculus complete?** `[open]` Not attempted.
5. **If accounting fails, what replaces mutual information?** `open to me` For a bounded observer, what x tells about y need not equal what y tells about x. A directed quantity is needed. The computational entropies of cryptography (HILL, Yao, unpredictability) look like pieces of it. `[proven · recall]` that they exist; that they assemble into one calculus is `[conjecture]`.
6. **Which curves are possible?** `open to me` The curve of distance against budget is smooth for coins and a cliff for parity. With two budgets, samples and computation, the object is a surface. The planted clique problem is believed to have a wide region where enough samples exist and no efficient test does: detection is statistically possible from clique size about 2 log2 n, and the known polynomial-time algorithms need about the square root of n. `[proven · checked]` that the gap is conjectural, not proved. Is there a classification of the shapes?
7. **One theorem behind exact accounting?** Independent and complete families of observers account exactly: remainders (section 5.3), primes (5.4), frequencies (5.2). Each is `[proven]`. That they are one theorem is `[conjecture]`. For the rationals, Tate's thesis may already be that theorem, `[proven · recall]` and unchecked. For budget-limited observers it is `open to me`.
8. **Is being fooled everywhere one phenomenon?** Selmer's cubic fools every standard observer of the rationals; a pseudorandom source fools every efficient observer. `[conjecture]` An analogy until someone states a common theorem. Number theory measures its failure with specific objects, the Brauer-Manin obstruction among them. `[proven · recall]`

## 9. What is and is not claimed

- Claimed: the definitions; the five laws and the calculus as consequences of them; the numbers, which the program reproduces; the accounts of other people's results where marked `checked`, to the depth stated.
- Not claimed: novelty for any law; completeness of the calculus; that the arrangement is a theory; anything marked `recall` beyond what a careful reader should verify before leaning on it.
- Known limits of the checking: sources were read at the level of abstracts and introductions unless stated; the random-model checks cover small finite models only; one model wrote both the notes and the program, so a second reader's run is worth more than a second run by the same author.

## Sources

Read in this session, at the depth stated above.

- [Regularity, Boosting, and Efficiently Simulating Every High-Entropy Distribution](https://salil.seas.harvard.edu/publications/regularity-boosting-and-efficiently-simulating-every-high-entropy-distribution), Trevisan, Tulsiani and Vadhan, 2009
- [Quantitative Algebraic Reasoning](https://www.macs.hw.ac.uk/~rm4023/papers/QA.pdf), Mardare, Panangaden and Plotkin, 2016
- [Quantitative Equational Logic](https://homes.cs.aau.dk/~grbacci/Papers/QA_JACM.pdf), Bacci, Mardare, Panangaden and Plotkin, 2026
- [Computational Indistinguishability Logic](https://dblp.uni-trier.de/rec/conf/ccs/BartheDKL10.html), Barthe, Daubignard, Kapron and Lakhnech, 2010
- [CIL Security Proof for a Password-Based Key Exchange](https://ro.uow.edu.au/eispapers/1836), Ene, Gritti and Lakhnech, 2013
- [On Equivalences, Metrics, and Polynomial Time](https://arxiv.org/pdf/1506.03710), Cappai and Dal Lago, 2015
- [On Computational Indistinguishability and Logical Relations](https://export.arxiv.org/pdf/2408.17340), Dal Lago, Galal and Giusti, 2024
- [Logical Foundations of Quantitative Equality](https://arxiv.org/pdf/2110.05388v1), Dagnino and Pasquali, 2021
- [Categorical Composable Cryptography](https://arxiv.org/pdf/2105.05949), 2021
- [A Duality Between One-Way Functions and Average-Case Symmetry of Information](https://eprint.iacr.org/2023/424), Hirahara, Ilango, Lu, Nanashima and Oliveira, 2023
- [A Counterexample to the Chain Rule for Conditional HILL Entropy](https://ia.cr/2014/678), Krenn, Pietrzak, Wadia and Wichs, 2016
- [On One-way Functions and Kolmogorov Complexity](https://arxiv.org/abs/2009.11514), Liu and Pass, 2020
- [The Enduring Scandal of Deduction](https://philarchive.org/archive/DAGTES-3v1), D'Agostino and Floridi, 2009
- [Logical Induction](https://arxiv.org/abs/1609.03543), Garrabrant, Benson-Tilsen, Critch, Soares and Taylor, 2016
- [Ostrowski's theorem](https://en.wikipedia.org/wiki/Ostrowski%27s_theorem), Wikipedia
- [Lectures on height zeta functions](https://arxiv.org/pdf/0812.0947), for the product formula and the ultrametric inequality
- [On Integral Probability Metrics, phi-Divergences and Binary Classification](https://arxiv.org/pdf/0901.2698v4.pdf), Sriperumbudur, Fukumizu, Gretton, Schölkopf and Lanckriet, 2009
- [Notes on Computational Hardness of Hypothesis Testing](https://arxiv.org/pdf/1907.11636), for the planted clique gap
- [Hasse principle](https://en.wikipedia.org/wiki/Hasse_principle), Wikipedia
- [A positive proportion of plane cubics fail the Hasse principle](https://arxiv.org/pdf/1402.1131), for Selmer's cubic
