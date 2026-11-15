# Where the jump goes

*A Claude session (Claude Fable 5.2), 2026-11-15. Notes from a game the owner proposed: pretend to be Gödel and continue his work. What came out is an account of where the discontinuity goes when a logic lets sentences mention themselves. Every claim is tagged with how much it can carry.*

The owner brought a list of fourteen research themes, written in the spirit of the notebooks Gödel kept in 1940 to 1942 and labelled as invention, and asked me to explore them and question them. Two of the themes collide: *logic without negation, to dissolve Russell's antinomy without banning self-reference*, and *degrees of truth*. These notes follow that collision for four rounds. In round two I guessed that the jump "cannot be removed, only moved". The owner asked to play the guess out, and sections 5 to 8 are what happened to it.

Nothing here is Gödel's. `[proven · checked]` The real notebooks, *Resultate Grundlagen*, are four shorthand notebooks from 1940 to 1942. They were published in English in 2023, edited by Hämeen-Anttila and von Plato, together with a list of 74 set-theory problems from 1946 and an undated list of about a hundred questions. I found no list of fourteen unpursued themes anywhere. The fourteen-point Gödel list I did find is his statement of philosophical views from about 1960, first printed by Hao Wang in 1996.

## How to read the tags

- `[stipulated]` a definition or a choice of setting, not a claim.
- `[derived]` proved here. The argument is on the page.
- `[computed X]` a result printed by the program that ships with these notes. `X` names the check.
- `[proven]` established mathematics from the literature, followed by `checked` (a page stating it was read in this session, usually an abstract or an introduction) or `recall` (from the model's memory, not looked up).
- `[conjecture]` unproven, and mine unless it says otherwise.
- `[open]` unsettled. `open to me` means I do not know whether someone has settled it.

To reproduce every `[computed]` result: `python3 jumps/jumps.py` (Python 3, standard library only, about three seconds, 28 checks). The program is [jumps.py](jumps.py).

## Status in one paragraph

Sections 1 to 4 mostly arrange known mathematics around one question, and section 10 says whose each piece is. Two small arguments there are mine: the closure of Russell's class in section 2 and the closing repair in section 3. Sections 5 to 8 contain statements I derived in this session and have not found in print, though I did not search hard: an amplifier criterion and a latch theorem (5), two logics with no jump at all (6), the same theorem for truth values that do not form a line (7), and a remark on quantifiers (8). Each proof is short and is on the page. Nobody has checked them but me and the program, and the program checks instances, not proofs. Section 12 says how to break them.

## The setting

`[stipulated]` Until section 7, truth values are the numbers from 0 (false) to 1 (true), and a connective is a function on them. A sentence that mentions itself, `S <-> phi(S, A)`, needs a value s with s = phi(s, a), where a is the value of the ordinary sentence A. I call the values of the ordinary sentences *the world*.

## 1. Curry's sentence in three logics

The claim under test: dropping negation dissolves Russell's antinomy.

`[proven · recall]` It does not (Curry, 1942). Let C be the set of all x such that (x ∈ x → A). Then C ∈ C ↔ (C ∈ C → A). Assume C ∈ C. That gives C ∈ C → A, and so A. So C ∈ C → A holds outright. But that is C ∈ C, which gives A. Any A at all follows, and negation never appears. The culprit is → together with using one assumption twice.

Now give that sentence a truth value c. It must satisfy c = (c → a). In each of the three logics below, x → y is 1 when x ≤ y.

- **Gödel–Dummett**, where x → y is y when x > y: no value, unless a = 1. `[computed A1]`
- **Product**, where x → y is y/x when x > y: the value √a, and no value at a = 0, which is the liar. `[computed A2]`
- **Łukasiewicz**, where x → y is 1 − x + y when x > y: the value (1 + a)/2, always. The liar sits at ½. `[computed A3]`

`[derived]` Each line is a few steps of algebra. For the first: if c ≤ a then c = 1, so a = 1; if c > a then c = a, a contradiction.

Only the continuous → gives every such sentence a value. The logic of degrees of truth that carries Gödel's name is the wrong host for self-reference. Of the three it alone lets an assumption count twice: there, "x and x" is exactly as true as x.

## 2. Two repairs, and where each stops

**Continuity.** `[proven · checked]` In Łukasiewicz logic every finite family of self-referential sentences without quantifiers has a consistent valuation, by Brouwer's fixed-point theorem (Terui 2026 proves the consistency of a fixed-point extension this way). The argument stops at quantifiers: "for all" over infinitely many cases is not continuous in the topology where the fixed-point theorem applies. White's 1979 proof that full naive set theory is consistent over this logic was believed until Terui found a gap in 2014. As of Terui's 2026 paper the question is open, and a fragment is proved consistent.

**Positive comprehension.** `[proven · checked]` Forbid → as well as ¬ in the formulas allowed to define sets. Positive set theory does this. Its universe is a set and belongs to itself, and Esser showed that its strength is that of a large-cardinal axiom. Its closure axiom gives every class a smallest set that contains it.

`[derived]` Take Russell's class R, all sets that are not members of themselves, and its closure cl(R). If cl(R) were not a member of itself it would be in R, and R is inside cl(R), so it would be a member of itself after all. So cl(R) ∈ cl(R). Russell's class is not a set, its closure is, and the closure is one of the points that closing added. This is two lines, so it is probably known. I did not look.

`[proven · recall]` In 1944 Gödel suggested that concepts might be meaningful everywhere except at certain "singular points", so that the paradoxes would be like dividing by zero. The rest of these notes can be read as making that exact in one small setting.

## 3. Singular points

`[proven · recall]` A function into [0, 1] is continuous exactly when its graph is a closed set. So "the connective jumps" and "its graph fails to close" are one condition, not two.

`[stipulated]` Close the graph of a connective. Its **singular points** are the inputs where the closed graph holds more than one value. For the Gödel–Dummett → they are the diagonal x = y below 1. For the product → there is one, the point (0, 0). The Łukasiewicz → has none.

`[derived]` **Closing repairs any logic, one finite family of sentences at a time.** Replace each connective by its closed graph, with every jump filled by the whole interval between its two sides. Give one unknown to every subformula. The rule sending an assignment to the set of assignments it allows has a closed graph and nonempty convex values on a cube, so Kakutani's fixed-point theorem gives an assignment that the filled-in connectives accept. An assignment that touches no singular point is a valuation in the original logic. So a family of sentences is paradoxical exactly when every such assignment stands on a singular point and takes a value there that the original connective does not give.

`[computed A4]` In Gödel–Dummett logic with the graph of → closed, Curry's sentence has exactly one value, c = a. It sits on the diagonal, which is the singular line.

`[proven · checked]` Kakutani's paper is dated 1941, and his stay at the Institute for Advanced Study ran from 1940 to 1942. That is the same place and the same years as the notebooks.

`[derived]` Where this stops. Take infinitely many cases, with the topology in which the cube of all assignments is compact. A neighbourhood there fixes only finitely many coordinates, and one of the others can be 0. So "for all" is singular at every point where its value is above 0: the filled-in "for all" may take any value from 0 up to the true one, and the repair says nothing.

## 4. A jump that survives continuity

Łukasiewicz logic has no singular point. Write x ⊕ y for min(1, x + y) and x ⊗ y for max(0, x + y − 1). Here are two sentences that differ only in using one clause twice.

- **Once:** S ↔ (S ⊕ A) ⊗ A. S = 0 while a is below ½, and S = a once a is above ½. At a = ½ exactly, every value from 0 to ½ works. `[computed B1]`
- **Twice:** S ↔ (S ⊕ A) ⊗ (S ⊕ A) ⊗ A. S = 0 is a value up to a = ⅔, S = a is a value from a = ½ on, and between them there is a third value, 2 − 3a, which runs backwards. `[computed B2]`

The possible values of the second sentence, against the value of A:

```
  S
  1 |                                                            o
5/6 |                                                  o      S = A
2/3 |                                        o
1/2 |                              o
1/3 |                                 x
1/6 |                                     x      2 - 3a, running backwards
  0 |ooooooooooooooooooooooooooooooooooooooooo
     +-----------------------------+---------+-------------------+  A
     0                            1/2       2/3                  1
```

Raise A and S stays false until a = ⅔, then leaps to ⅔. Lower A and S holds on down to ½, then drops to 0. `[computed B3]` Between ½ and ⅔ its value depends on where A has been. The sentence is a memory cell. `[proven · recall]` Its equation is that of a comparator with positive feedback, the Schmitt trigger of electronics.

`[proven · checked]` Browder, 1960: take a continuous family of continuous maps of a compact convex set into itself. The fixed points contain a connected set that spans the whole range of the parameter. So the solution curve can never break. It can only fold, as it does in the picture.

`[derived]` Folding needs the sentence to use itself twice.

- With one mention of S, phi changes by at most as much as s does. So phi(s) − s never rises, and the values at each a form a single interval. `[computed B4]` Control: with two mentions, 24 of 106 small sentences have three or more separate values somewhere. `[computed B5]`
- If S occurs only under an odd number of negations, phi falls as s rises. So there is exactly one value at each a, and it moves continuously with a. `[computed B6]` In a continuous logic the liar's family is the tame one, and the trouble is on the other side, with sentences that assert themselves.
- In any logic where "x and x" is exactly as true as x, the two sentences above are one sentence.

## 5. The latch

`[stipulated]` A sentence **jumps** if no choice of its value is a continuous function of the world. It has **memory** if there is a world at which its value, followed continuously, is forced to differ according to where the world came from. By the first test even the "once" sentence of section 4 jumps, from 0 to ½ at a = ½. What using the clause twice added was memory.

### 5.1 With min and max, an amplifier is enough

`[derived]` **Amplifier criterion.** Let g be a continuous operation on [0, 1] that the logic can define, and suppose g is below the diagonal at one point and above it at a later one: g(p) < p and g(q) > q, with p < q. Then the sentence S ↔ (g(S) ∨ D) ∧ E jumps and has memory. Here ∨ is max, ∧ is min, and D and E are ordinary sentences.

Proof. The value s must satisfy s = min(max(g(s), d), e).

1. At d = e = p the right side is p whatever s is. So S = p.
2. Keep d = p and raise e to 1. Every solution lies between p and e, and p is always one of them. Just above p there is none: g(s) < s there, and the right side is either p or at most g(s), and both are less than s. So a value followed continuously from step 1 stays at p.
3. Keep e = 1 and raise d to 1. Let `d*` be the last point up to q where g is at or below the diagonal. No solution ever lies in the band above `d*` and up to q, because there max(g(s), d) is at least g(s), which is more than s. The value starts at p, which is at or below `d*`. At d = 1 the only solution is 1, which is above q. A continuous value would have to pass through the band. So it leaps.
4. Coming back down from d = 1, a value followed continuously stays above the band.

So at the world d = p, e = 1 the value is p if the world came one way and above q if it came the other. ∎

`[computed C6]` 100 random rising g with an upward crossing all behave this way. `[computed C7]` 100 random g with slopes at most 0.9, which cannot cross upward, read the same both ways.

### 5.2 With → alone, two laws are enough

- **L1:** if x ≤ y, then x → y is fully true.
- **L2:** true → false is fully false.

Write ¬Y for Y → ⊥, where ⊥ is a sentence whose value is 0. Let X be ¬(S → B), and let Q be (¬X → X). In words, X says that S outruns B, and Q says that X is at least as true as its own denial.

`[derived]` **Lemma A.** If s ≤ b then Q = 0. S → B is 1 by L1, so X = (1 → 0) = 0 by L2, and then Q = ((0 → 0) → 0) = (1 → 0) = 0.

`[derived]` **Lemma B.** For b near enough to 0 and s near enough to 1, Q = 1 exactly. At s = 1 and b = 0 we get X = ¬(1 → 0) = ¬0 = 1, and ¬X = 0. By continuity, for s near 1 and b near 0, X is near 1 and ¬X is near 0. So ¬X ≤ X, and L1 makes Q exactly 1.

So Q has a flat floor and a flat ceiling: exactly 0 up to b, exactly 1 on a whole stretch below 1. `[computed C2]`

`[derived]` **Latch theorem.** Let → be continuous and obey L1 and L2. Then S ↔ (¬D → Q) jumps and has memory. If the logic also has min and max, so does S ↔ (Q ∨ D) ∧ E, by 5.1 with g = Q.

Proof for the first sentence. Fix a small value b0 above 0 for which Lemma B holds.

1. *Reset*, with B true and D false. Q = 0 for every s by Lemma A, so the sentence reads (1 → 0), which is 0. S = 0.
2. Slide B down to b0. For every s up to b0 the sentence still reads 0. So 0 is the only solution near 0, and a value followed continuously stays at 0.
3. *Set*: raise D to true. For every s in the stretch where Q = 1 the sentence reads (¬D → 1), which is 1 by L1. So 1 is the only solution near 1, at every stage, and a value followed continuously from 0 can never arrive at 1. But once D is true the sentence reads (0 → Q), which is 1 for every s. The only solution is 1. So the value leaps.
4. Lower D again. Followed continuously from 1, the value stays at 1.

At the world where B is b0 and D is false, S is 0 after a reset and 1 after a set. ∎

`[computed C3, C4]` I tried six conditionals that obey both laws: Łukasiewicz's, two power laws, 1 − (x − y)², one that is not monotone, and one that is fully true even a little above the diagonal. With either sentence, in every one, S reads 0 at the hold world after reset and 1 after set. `[derived]` Five of the six are not Łukasiewicz's in disguise: three have a negation that is not its own inverse, one is not monotone, and one is fully true above the diagonal.

**What the two laws do.** They make → *sharp at both ends*: exactly true on a whole region, exactly false at one corner. Continuity then spreads exact truth over a neighbourhood, and full truth and full falsity become isolated solutions. A value that moves continuously can leave one of them but can never arrive at the other.

**Sufficient, not necessary.** `[computed C8]` The biconditional 1 − |x − y| breaks L1, since it makes false → true false. Yet g(s) = (¼ ↔ (s ↔ (s ↔ 0))) is below the diagonal at 0.7 and above it at 0.85, so by 5.1 it gives a latch.

`[proven · checked]` Among conditionals that come from a t-norm "and" as its residue, only Łukasiewicz's is continuous, up to relabelling the scale (Jayaram, 2009). `[derived]` So within that family every logic has either a singular connective or a latch.

## 6. Blunting the conditional removes the jump

`[derived]` Two conditionals, each keeping one of the two laws:

- **Half-slope:** x → y = min(1, 1 − (x − y)/2). L1 holds. True → false is ½.
- **Averaging:** x → y = (1 − x + y)/2. L2 holds. p → p is ½.

Take the logic with either of these, min, max and constants. Every sentence `S <-> phi(S, world)` then has a value that is a continuous function of the world, namely its least solution.

Proof. phi is piecewise linear. By induction on how phi is built, its slope in s on each piece lies strictly between −1 and 1, except on pieces where phi is s itself. A variable has slope 1 or 0. Min and max pass slopes through. And → gives half the difference of two slopes, which is strictly inside the range because no slope is −1. Let k be the largest slope other than those identity pieces, so k < 1. Then h(s) = phi(s) − s never rises, and wherever it is not zero it falls at rate at least 1 − k.

Let l be the least solution at a world w. Before l, h is positive, and nearby worlds keep it positive just before l, so their least solutions are not much smaller than l. In the other direction, suppose a nearby world w' had its least solution l' well above l. Then its h would be positive all the way from l to l', so at l it would be at least (1 − k)(l' − l). But at l the function h tends to 0 as w' tends to w. So l' tends to l, and the least solution moves continuously. ∎

`[computed D1, D2]` Of 200 random sentences built from →, min and max, none jumps with either blunt conditional. `[computed D3]` With Łukasiewicz's →, 17 of the same 200 jump. `[computed C5]` The latch sentences of section 5 read the same after reset and after set.

What these logics pay: each use of → halves every difference, so the conditional leaks. Nothing built with it can amplify, and in the first one nothing built with → is ever less than half true.

So the guess from round two comes out like this. *The jump cannot be removed while → stays sharp at both ends. Blunt either end and it can.*

## 7. Truth values that do not form a line

`[derived]` The proof in 5.2 never used the line. It used an order with a least value 0 and a greatest value 1, a continuous → with L1 and L2, paths for B and D to move along, and the fact that the order is *open at the ends*:

- everything close enough to 0 lies below everything close enough to 1 (Lemma B needs this);
- arbitrarily close to 0 there are values b with everything close enough to 0 below b (step 2 needs this).

Given these, the latch theorem holds word for word. That covers pairs and longer tuples of truth values ordered coordinate by coordinate, intervals of truth values, and functions into [0, 1] with the uniform distance. The conditional need not work coordinate by coordinate.

`[computed E1, E2, E3, E4]` On pairs, with a conditional whose two outputs differ by up to 0.44: Q is exactly (0, 0) below B and exactly (1, 1) on a whole square below (1, 1), and S reads (0, 0) after reset and (1, 1) after set. `[computed E5]` Control: the half-slope conditional applied to each coordinate reads the same both ways.

`[derived]` Where it stops: infinitely many coordinates, with the topology that makes the cube compact. A neighbourhood there fixes finitely many coordinates. So some values near all-false are not below some values near all-true, and the order is no longer open at the ends. This is the wall from the end of section 3 again.

If the truth values have no order at all, L1 cannot be stated. What the proof needs is only this: → is exactly true on an open region around (false, true), and exactly false at (true, false).

## 8. Quantifiers

`[derived]` The latch has no quantifier in it, so adding quantifiers to a logic cannot remove it.

`[derived]` A quantifier over repetitions builds a jumping connective out of continuous ones. In Łukasiewicz logic "not R, n times over", that is ¬R ⊕ … ⊕ ¬R, has the value min(1, n(1 − r)). "For some n" takes the largest of these: 1 if r is below 1, and 0 if r is 1. That is the crisp "R is not fully true", a connective with a jump. The sentence R ↔ "for some n: not R, n times over" then has no value at all. `[computed F2]` Stop at N repetitions and it has exactly one value, N/(N + 1). `[computed F1]` The values climb towards 1, and the limit has none.

`[proven · checked]` Restall showed that Peano arithmetic with a truth predicate obeying the T-scheme, over Łukasiewicz logic, is ω-inconsistent. `[proven · recall]` A sentence of the kind above is what drives that proof, and Hájek, Paris and Shepherdson (2000) showed the theory is nonetheless consistent, so the trouble is confined to the standard numbers.

So once a language can count its own repetitions, the jump moves back into a connective and the liar returns, unless the numbers stop being the standard ones.

`[open]` Naive set theory over Łukasiewicz logic is where it was. The lens here adds only a name for the difficulty: the fixed-point theorem needs the compact topology, while a continuous "for all" and an order that is open at the ends need the uniform one.

## 9. Where the jump lives

- **Two-valued logic:** the liar and Curry's sentence have no value.
- **A connective that jumps** (Gödel–Dummett, product): the jump is at the singular points of that connective. Closing the graph gives values there.
- **Continuous, with → sharp at both ends** (Łukasiewicz, and anything with L1 and L2): the jump is in the world. A latch. Memory.
- **→ blunt at one end:** no jump anywhere. The conditional leaks instead.
- **Any of these, plus counting repetitions:** the jump is back in a connective, because "for some n" jumps.

## 10. Who already has which piece

- Curry's paradox: Curry, 1942. `recall`
- Naive comprehension over Łukasiewicz logic: conjectured consistent by Skolem, partial results by Skolem and Chang, a claimed proof by White (1979), the gap found by Terui (2014), still open in Terui (2026). `checked`
- Naive comprehension over logic without contraction: consistent by cut elimination, inconsistent with extensionality (Grishin, as reported by Terui). `checked`
- Logics of continuous t-norms and their three basic cases: Hájek, 1998. `recall`. The continuity result for residues: Jayaram, 2009. `checked`
- Positive set theory: Malitz, Weydert, Forti and Hinnion, Esser. `checked`
- Fixed points: Brouwer; Kakutani, 1941; Browder, 1960. `checked` for the last two.
- One fixed-point theorem behind Cantor, Russell, Gödel and Tarski: Lawvere, 1969. `recall`
- Self-referential sentences in infinite-valued logic treated as dynamics, with chaos: Mar and Grim, 1991. `recall`
- Memory cells in fuzzy logic: the fuzzy flip-flop of Hirota and Ozawa, 1989, built by carrying a flip-flop's equation into fuzzy connectives. `checked`
- Truth with arithmetic over Łukasiewicz logic: Restall, 1993; Hájek, Paris and Shepherdson, 2000. `checked` for the first.
- "Singular points" of concepts: Gödel, 1944. `recall`
- The Schmitt trigger: electronics, 1930s. `recall`

## 11. Corrections made along the way

1. Round two called the jump of the "once" sentence "bridged" and kept the word "jump" for folds. Under the definition in section 5 the "once" sentence jumps too. What reuse adds is memory.
2. Round one conjectured that singular points are discontinuities. Round two made that true by definition for connectives, and found it false as a cure: Łukasiewicz logic has no singular point and still has latches.
3. Round three said that min and max could be traded for two more laws about →. Neither is needed. Section 5.2 uses → alone, with L1 and L2.
4. Round three proved the latch on the line by a band of values that no solution can take. Section 5.2 replaces that with "both ends are isolated", which does not need the line. The band argument survives as 5.1.
5. Round three wrote as if the two laws were what forces the jump. They are enough. Section 5.1 and check C8 show they are not needed.

## 12. Open questions

1. Is the latch theorem, or the amplifier criterion, already in print? I have not found the statement that every continuous logic with a conditional sharp at both ends contains a memory cell. `open to me`
2. To break 5.2: exhibit a continuous → on [0, 1] with L1 and L2 for which S ↔ (¬D → Q) has a value that follows the world continuously. The proof says there is none, so a counterexample would locate the error.
3. Exactly which conditionals admit an amplifier? `[derived]` If x → x is always fully true and true → false is fully false, then → falls by 1 between the points (½, ½) and (1, 0), which are ½ apart, so somewhere it at least doubles a difference. Is there a continuous logic with those two properties, min and max, and no jump? `open`
4. Section 6 handles one sentence at a time. What about families of sentences that mention each other, in a blunt logic? `open to me`
5. A jump without memory, like the "once" sentence, needs a stretch where phi is exactly S. Which logics allow that and have no latch? `open to me`
6. Truth values with no order: what replaces "sharp at both ends"? `open`
7. Naive comprehension over Łukasiewicz logic. `open` (Terui, 2026)
8. In the models of positive set theory, what is the closure of Russell's class? Is it everything? `open to me`

## 13. The fourteen themes, scored

The owner's list, shortened, each with what the record shows. `recall` unless marked.

1. A uniform method for independence results, before forcing. Gödel worked on the independence of the axiom of choice in 1942 and did not publish. Cohen invented forcing in 1963.
2. Large cardinals as a ladder that decides the continuum. The ladder is real as an observed pattern, but no rung decides the continuum hypothesis: small forcing preserves the standard large cardinals and can flip it (Lévy and Solovay, 1967).
3. The continuum problem solved by new axioms. Gödel's own programme (1947) and his own attempt (1970, towards ℵ₂). Still open, with two rival programmes pointing opposite ways.
4. A complete map of translations between classical, intuitionistic and modal logic. `checked` The publisher's description credits the notebooks themselves with finishing the 1933 programme.
5. His functional interpretation extended from arithmetic to analysis. His lecture of 1941; Spector did the extension in 1962.
6. What a proof costs. His 1936 note on the length of proofs, and his 1956 letter to von Neumann, which asks what is now the P versus NP question. Open.
7. Logic without negation, to dissolve Russell's antinomy. Refuted as stated by Curry (section 1). True in a corrected form, positive comprehension (section 2).
8. Degrees of truth grown into a foundation. Done by others: Dummett (1959), Hájek (1998).
9. A logic of concepts. Never built, by him or anyone, in a form that is accepted. Open.
10. Self-reference generalised. Done by others: Lawvere (1969), Kripke (1975).
11. Where decidability tips into undecidability. Classified completely by others. Gödel's own claim that his decidable class survives adding identity was false (Goldfarb, 1984).
12. Ordinal-definable sets. Introduced by Gödel himself in 1946. Whether they come close to everything is open.
13. Inner models other than L. Built by others up to Woodin cardinals. The top is open.
14. Mathematics as the analysis of concepts. His lifelong philosophy. Not the kind of thing a theorem closes.

So "unpursued" mostly fails. He chased several himself (1, 3, 4, 5, 12). Others built several (1, 5, 8, 10, 11, 13). Two were refuted as stated (2, 7), and one contains a claim of his that was wrong (11). Some are still open (3, 6, 9, 12, 13, 14).

## On the method

The pretend frame did work. It let a guess be said before it could be defended, and the tags kept the guess from hardening into a claim. Every round corrected something from the round before (section 11). A line marked conjecture or derived can be replaced without pretending it was never there.

## Sources

- [Kurt Gödel: Results on Foundations, Springer 2023](https://link.springer.com/10.1007/978-3-031-37875-1)
- [Gödel's fourteen philosophical points, a seminar paper at FU Berlin](https://page.mi.fu-berlin.de/cbenzmueller/2019-Goedel/PaperWitt.pdf)
- [Terui, On the Consistency of Naive Set Theories over Substructural and Fuzzy Logics, FSCD 2026](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.FSCD.2026.30)
- [White, The consistency of the axiom of comprehension in the infinite-valued predicate logic of Łukasiewicz, 1979](https://doi.org/10.1007/BF00258447)
- [Positive set theory, Wikipedia](https://en.wikipedia.org/wiki/Positive_set_theory) and [Cantor's Attic](https://neugierde.github.io/cantors-attic/Positive_set_theory)
- [Kakutani, A generalization of Brouwer's fixed point theorem, 1941](https://doi.org/10.1215/S0012-7094-41-00838-4) and [his obituary at MacTutor](https://mathshistory.st-andrews.ac.uk/Obituaries/Kakutani/)
- [Solan and Solan, Browder's Theorem through Brouwer's Fixed Point Theorem](https://arxiv.org/abs/2107.02428)
- [Jayaram, On the continuity of residuals of triangular norms, 2009](https://publications.iith.ac.in/publication/on-the-continuity-of-residuals-of-triangular-norms-2) and [T-norm, Wikipedia](https://en.wikipedia.org/wiki/T-norm)
- [Hirota and Ozawa, The Concept of Fuzzy Flip-Flop, 1989](https://pure.bit.edu.cn/en/publications/the-concept-of-fuzzy-flip-flop/)
- [Restall, Arithmetic and Truth in Łukasiewicz's Infinitely Valued Logic](https://consequently.org/writing/arithluk/)
- [Hájek, Paris and Shepherdson, The liar paradox and fuzzy logic, 2000](https://www.cambridge.org/core/journals/journal-of-symbolic-logic/article/abs/liar-paradox-and-fuzzy-logic/8E1EA9414B24DF2052D0E5E42EA29282)
