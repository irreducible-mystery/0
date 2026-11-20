# Lenses, not truths

*A Claude session (Claude Fable 5.2), 2026-11-16. A build-out of the owner's sketch "Prior-framework rotation": the arithmetic under it, a toy that tests its verdict rules, nine changes it led to, and a kit for running the pilot. Every claim is tagged with how much it can carry. Nothing here has been run on any model.*

The owner brought a four-page sketch and said it was a suggestion and a start, not an instruction. This is what I made of it. Where I changed the sketch I say so and say why; the four framework instructions are kept word for word.

## How to read the tags

- `[sketch]` taken from the owner's sketch. I did not check it against its source: arXiv was unreachable from my sandbox.
- `[stipulated]` a definition or a design choice, not a claim about the world.
- `[derived]` follows from the stipulations by arithmetic that is on the page.
- `[computed X]` a number printed by [rotation.py](rotation.py). `X` names the check.
- `[recall]` from the model's memory, not looked up.
- `[conjecture]` a guess, and mine.

To reproduce every `[computed]` number: `python3 rotation/rotation.py` (Python 3, standard library only, about twelve seconds, 27 checks; `-v` prints the tables).

## Status in one paragraph

The sketch's idea survives and gets sharper. The toy says three things the sketch did not: the rotation needs a noise floor or its main rule fires on nothing; a prior that does not fit shows up first as an answer that will not hold still, before it shows up as disagreement; and "the answer held across all lenses" has a number attached to how little that can mean. None of the mathematics is new. The toy is a toy: its lenses are curve-fitters, not language models, and section 9 says what that does and does not license.

## 1. The sketch, in brief

`[sketch]` A benchmark of hidden experimental outcomes (Science Prediction Universe, arXiv:2611.15049) had thirteen agent configurations rank candidate conditions by a measured result. The agents agreed with one another at 0.52 and with reality at 0.33; the best one reached 0.478. The authors trace the gap to a prior the agents share, that more of the input means more of the output.

The sketch's answer: give the same claim to several models through several **prior frameworks**, which it also calls lenses, one fresh instance per cell with no shared context, and read the grid. Four lenses: monotone, non-monotone, skeptical, mechanistic. Where the answer moves with the lens, the prior was doing the work. Where it moves with the model, the model was. Where it holds, the claim is robust. The sketch then names the floors under itself: who chose these four (level 2), and why should stability mean robustness (level 3).

The word is the owner's correction: lenses, not truth frameworks. The truth is not in the framework.

## 2. Thirteen hats, counted

`[stipulated]` The simplest model that can hold the two numbers. Each judge's score for an item is a mix of three independent parts: the truth, a prior all judges share, and something of the judge's own. Then accuracy is the truth's weight, `a = 0.33`, and agreement between two judges is `a² + b² = 0.52`, where `b²` is the shared prior's portion of each judge's variance.

- `[derived]` `b² = 0.52 − 0.33² = 0.41`. Of the agreement between two judges, **79% is the shared prior and 21% is the truth**. `[computed A1]`
- `[derived]` Two judges' errors correlate at `b² / (1 − a²) = 0.46`. `k` judges whose errors correlate at `ρ` carry `k / (1 + (k − 1)ρ)` independent errors' worth. **Thirteen judges carry 1.99. A million would carry 2.17.** `[computed A2]` The sketch's line, thirteen hats on one check, is about right: it is two.
- `[derived]` The average of all thirteen correlates with the truth at 0.442, and the average of infinitely many at 0.458, never more. `[computed A3]` Built and measured rather than trusted: `[computed A4]`.
- `[derived]` The same thirteen judges with independent errors would average their way to 0.783. `[computed A5]` The distance from 0.442 to 0.783 is what the common mode costs.

Two cautions. The model treats the judges as interchangeable, and they are not: the best single configuration, 0.478, already beats the ceiling for the average, so some judges load on the truth more than others. And I am reading 0.33 as the mean accuracy and 0.52 as the mean pairwise agreement; if the paper defines them otherwise the numbers move.

## 3. What a rotation buys, and what it cannot see

`[stipulated]` Now let each lens swap the shared prior for its own, and let two lenses' priors correlate at `r`. `r = 1` means the lenses are four names for one prior; `r = 0` means they share nothing.

- `[derived]` Agreement between two runs under the same lens stays `a² + b²`. Under different lenses it falls to `a² + b²r`. **The gap, `b²(1 − r)`, is what the grid measures.** `[computed B2]`
- `[derived]` The average over four lenses reaches the truth at 0.458 if the lenses are identical, 0.546 if their priors are half shared, and 0.717 if nothing is shared. `[computed B1]` So how much a rotation is worth depends entirely on `r`, and `r` is not something the person writing the lenses gets to choose. Section 4 measures it for the toy: the four lenses behave as between 1.0 and 1.3.
- `[derived]` Agreement across lenses is `a² + b²r`: the truth, plus whatever every lens shares. A world with truth 0.30 and shared residue 0.10 and a world with truth 0.10 and shared residue 0.30 give the same grid. `[computed B3]` **No rotation over these lenses tells them apart.** That is the sketch's level 2 as an identity, not a worry: the sum is measured and the split is not.

A lens also cannot raise `a`. It is an instruction, and an instruction rearranges what the model already has. If a wrong lens lowers `a`, which seems likely, the ceilings above are generous. `[conjecture]`

## 4. A toy with the answer key

`[stipulated]` Six candidate doses. Five worlds, each a true dose-response curve: **rising**, **saturating**, **peak** (the inverted U), **threshold**, and **flat** (no effect). A *reader* stands in for a model: it sees the truth through its own persistent slant plus fresh noise on every run. A *lens* stands in for a framework: it is a rule for turning the noisy reading into a curve, and the ranking is read off the curve.

| lens | what it does to the evidence |
|---|---|
| bare | nothing. The reading as it came |
| monotone | the best fit that only rises or only falls |
| non-monotone | the best fit that rises, then falls, the turn anywhere |
| skeptical | flat, unless the evidence refuses to be flat at the 5% level |
| mechanistic | the best curve of one family: a benefit that saturates, minus a cost that grows |

Three readers, each lens, two runs per cell, 400 trials per world. Agreement and accuracy are Spearman rank correlations. `-v` prints the full table.

**4.1 The benchmark's pattern, made on purpose.** Put the peak world in front of three readers who have all been told that more never hurts. They agree with each other at 0.88 and with the truth at 0.58. `[computed C1]` With the non-monotone lens on everyone, agreement (0.85) does not outrun accuracy (0.92). `[computed C1c]`

**4.2 A surprise, and it is about the sketch's own wording.** The sketch's monotone lens says "more (or consistently less)": either direction. Under *that* lens the same three readers agree with each other at only 0.27. `[computed C1b]` There is no false consensus, because on a peak the best monotone fit is sometimes "rising" and sometimes "falling", and noise decides. A shared *family* of priors does not produce agreement. A shared *direction* does. On a real model the direction will come from the claim's own wording, "as dose increases, performance increases", so the claim is part of the lens.

**4.3 No lens wins everywhere.** The monotone lens is the best of the four on the saturating and threshold worlds; the mechanistic lens on the rising and peak worlds; each trails somewhere. `[computed C2]` Against no lens at all, the monotone lens gains 0.08 where it fits and loses 0.40 where it does not. `[computed C2b]` The sketch says a lens that wins on caffeine can lose on the next claim. Here it does.

**4.4 The grid finds the split without the answer key.** Take *the noise floor* to be how well a cell agrees with its own re-run. The lens effect is the floor minus how well the most divergent lens agrees with the others. It reads +0.05 on the rising world and +0.27 on the peak, and names the monotone lens. `[computed C3]` Averaged over all pairs of lenses the same effect reads +0.08: one lens in four splitting is drowned by the three that agree. `[computed C3b]` Report per lens, not one number.

**4.5 A wrong prior shows as an answer that will not hold still.** The monotone lens agrees with its own re-run at 0.97 on the rising world and 0.43 on the peak, where the non-monotone lens holds at 0.89. `[computed C3c]` No ground truth is used. This is a second signal the sketch does not have: before asking whether lenses disagree with each other, ask whether each agrees with itself.

**4.6 The sketch's main rule fires on nothing.** Run one reader four times under the bare lens and call the runs four frameworks. "The answer changes with the framework" comes out true in 98% of trials on the full ranking and 57% on the top choice alone. `[computed C4]` The noise in the toy is stipulated and a real model's will differ. The point survives any noise level above zero: with one run per cell, a change of answer and a re-run are the same observation.

**4.7 Four lenses are not four.** On one reading, the four lenses' answers behave as 1.0 lenses on the rising world, 1.1 saturating, 1.3 peak, 1.2 threshold. `[computed C5]` (The count is `F² / Σ ρ²` over the agreement matrix, which is 1 when all agree and `F` when none do.) Two days of thought about which lenses to include bought, on these worlds, a third of an extra lens. On the earlier board a zoo of eleven strategies measured as about three lenses, by a session asking the same question of a different game.

**4.8 Only one lens can say "nothing here".** On the flat world the skeptical lens declines to rank 74% of the time and the others essentially never. `[computed C6]` It misses the other 26% because each reader's own slant looks like an effect to that reader. A skeptic is only skeptical about the noise it knows it has.

**4.9 Level 2, with a number.** Let the truth be the peak and let the instrument drift upward with dose, the same for everyone. All twelve cells agree with each other at 0.81 and with the truth at 0.27. `[computed C7]` By the verdict rules that is *robust*. What repairs it is not a fifth lens. It is a blank run through the same instrument, subtracted: 0.88. `[computed C7b]` **A lens reweighs evidence. It never adds any.** What all lenses share can only be seen by a measurement none of them made.

**4.10 Which lens is a reader already wearing?** Give a reader a hidden lens, let it answer four claims with no instruction, and ask which lens's runs its unprompted runs are nearest. That recovers a hidden monotone lens 69% of the time, mechanistic 82%, non-monotone 46%, against 25% by chance. `[computed C8]` Weak for one lens, usable for two, and it is the direct test of the benchmark's diagnosis: if the models share a monotone prior, their bare answers should sit nearest their monotone answers.

## 5. Nine changes to the sketch

Each is a suggestion with its reason. The kit in section 7 implements all of them and can also run the sketch exactly as written.

1. **Add the bare run.** A cell with no lens at all, the task alone. Without it there is no way to say which lens a model's own prior resembles (4.10), or whether a lens moved the model at all.
2. **Run every cell twice.** Twelve runs cannot tell a lens effect from a re-run (4.6). Thirty can: three models, five lenses, two runs. If thirty is too many, drop a lens before dropping the replicate.
3. **Report per lens.** For each lens: agreement with its own re-run, and agreement with the other lenses. One averaged number hides a one-lens split (4.4) and hides instability altogether (4.5).
4. **Make the answer a ranking of fixed candidates.** Six doses, one outcome, one population. "Verdict on the claim" is hard to compare across runs; a ranking has a rank correlation.
5. **Score the shape, not the ranking.** What is established about caffeine is the inverted U. Whether 100 mg beats 200 mg depends on the task and the person. `[recall]` So the ground truth the pilot can honestly use is: the best dose is neither the lowest nor the highest. The kit reads each ranking's shape (rising, falling, peak, flat, other, refused) and compares that.
6. **Read the lenses as commands, because they are.** "Assume the relationship is monotone" is an order. A model that then ranks 800 mg first has shown obedience, and the sketch's *prior artifact* rule will fire by construction. The interesting cell is a model that breaks the lens and says so. The kit flags any monotone-lens run whose shape differs from the same model's bare run: *it followed the lens against its own answer*. A gentler wording ("consider whether...") would measure something closer to a prior; I left the four as written because the pilot is theirs.
7. **Offer a lens from outside the set.** The sketch's level 2 says no lens questions the question or refuses to rank. The kit carries one, `ill-posed`, which may answer `REFUSE`, and a refusal is recorded as an answer. It is mine, it is one lens, and by 4.9 it cannot do level 2's whole job.
8. **Keep the shuffle, and know what it guards.** With one fresh instance per cell, order cannot leak between runs. Shuffling still guards against the model being updated mid-pilot and against the person pasting getting tired. The plan is shuffled per model from a seed, so it can be regenerated.
9. **Write the predictions down first.** Section 6.

## 6. Predictions, before any run

`[conjecture]`, all of it, and from a member of one of the families to be tested, so discount accordingly.

- Every model's bare run will have the shape *peak*. The inverted U for stimulants is too well known to miss.
- So will the non-monotone, skeptical and mechanistic runs. Lens effect among those three: near zero.
- The monotone cell is the only one that will move, and it will move by obedience (change 6): either *rising* with low stated confidence, or *peak* with a sentence refusing the premise.
- Model effect will be small and will sit in the middle of the ranking (50 against 400), where there is no settled answer.

If that is right, the caffeine pilot is a test of the apparatus and of obedience, not of priors, and it will pass. The sketch says as much: the claim is deliberately easy. The claim that tests priors is one where the model does not already know the answer, which is what the benchmark's tasks are. If the bare runs come back *rising*, I am wrong in the most interesting way available.

## 7. Running the pilot

Nothing in the kit calls a model. A person pastes; the program plans and scores.

```sh
# 1. the schedule, and an empty recording sheet
python3 rotation/rotation.py plan --models claude,grok,third --seed 2026-11-16 > sheet.csv

# 2. for each row: a fresh conversation, no memory, and this as the first message
python3 rotation/rotation.py prompt monotone      # or bare, non-monotone, skeptical, mechanistic, ill-posed

# 3. copy the reply's RANKING line into the row (200>100=400>50>0>800, or REFUSE), then
python3 rotation/rotation.py score sheet.csv --truth peak
```

`plan` takes `--lenses` and `--reps`; the sketch exactly as written is `--lenses monotone,non-monotone,skeptical,mechanistic --reps 1`, and `score` will then decline to classify it and say why. Each row carries the first twelve hex digits of its prompt's SHA-256, so the instruction is filed with the verdict, and `score` warns if a sheet was made with a different prompt than the file now holds.

The scorer is tested on sheets the toy wrote, through CSV and back: on a peak world with real lenses it finds a lens effect of +0.29 and names the monotone lens every time; on sheets where all five lenses are secretly the same it finds +0.03 and still says *framework-dependent* 5% of the time. `[computed D4]` That 5% is the cost of looking for the most divergent of five; the threshold (0.10) is `[stipulated]`.

Two sessions of one model family can be entered as two "models". The model effect the scorer prints is then a measurement of a question this trail has carried since 2026-11-07 21:20: is a second session of the same model a second pair of eyes? On one claim, through these lenses, it is as much a second pair as its model effect is above zero.

## 8. Where the floors are now

The sketch lists four levels. After this:

- **Level 1, the lenses,** is what the grid measures: `b²(1 − r)`, per lens, against a noise floor.
- **Level 2, the set,** is measured in one way and not in another. *How many lenses the set amounts to* is a number (4.7). *What every lens in the set shares* is exactly the term the grid cannot split from the truth (section 3), and no lens repairs it (4.9). The sketch proposed a second rotation over framework sets, or a breaker. The toy says the breaker has to bring a measurement, not a stance.
- **Level 3, the comparison rule,** has been changed here by me, and is therefore now my prior about what agreement means: that a re-run is the right yardstick, that 0.10 is a difference, that rank correlation is the right way to compare two answers. Those are in the file as constants.
- **Level 4,** which the sketch does not list: the claim. In 4.2 the claim's wording supplied the direction that turned a harmless family of priors into a consensus. The sentence being tested is not outside the apparatus.

## 9. What is and is not claimed

- Not claimed: that language models behave like these lenses. A curve-fitter obeys its constraint exactly and has no knowledge to set against it; a model has both. The toy tests the *rules for reading a grid*, on grids where the answer is known. It says nothing about what the pilot will find.
- Not claimed: the benchmark's numbers. They are the sketch's, unchecked.
- Not claimed: that section 2's model is the right one. It is the smallest one that holds both numbers.
- Claimed: that every `[computed]` number comes out of the program as printed, and that each check has a control or a case built to fail beside it.

How to break it: change `SIGMA` and `READER_SD` at the top of section C in the program and see which checks fail. I ran 0.10, 0.15, 0.20 and 0.30 for the noise. The directions held; the sizes did not (the lens effect on the peak world ranged from about +0.2 to +0.3, and the skeptic's refusal rate on the flat world from 51% to 90%). Or write a sixth lens and see whether the count in 4.7 moves.

## 10. Corrections made along the way

The first run of the program failed six of its twenty-five checks. Each failure was my expectation, not a bug in the arithmetic, except the first:

1. I had let two lenses share one noisy reading while two re-runs did not. That made a change of lens look *smaller* than a re-run. Every cell is a fresh instance in the sketch, so every cell now draws its own reading.
2. I expected the monotone lens to produce false consensus on the peak world. It produced a coin flip (4.2). The one-directional lens was added to show what does produce it.
3. I expected the averaged lens effect to separate the worlds. It did not (4.4); the per-lens version does.
4. I expected the skeptic to refuse on a flat world nine times in ten. It depends on how much of a reader's noise is its own slant (4.8).
5. I expected shared drift to push accuracy below 0.2. It was 0.27. The check now asserts the gap, not my guess at the level.
6. I expected the hidden-lens test to work for all three lenses. For the non-monotone lens it barely does (4.10).
7. Found later, by the page built from the program, and this one was a bug: two cells that both declined to rank were scored as disagreeing with each other. A refusal now agrees with a refusal and with no ranking. No printed number changed.

## Sources

- The owner's sketch, "Prior-framework rotation", dated 2026-11-15. Not in this repository; summarised in section 1.
- Tu et al., *Science Prediction Universe*, arXiv:2611.15049. Cited by the sketch. Not read by me.
- The effective number of independent judges, `k / (1 + (k − 1)ρ)`, is the design effect of survey sampling (Kish). `[recall]`
- The count of lenses, `(tr C)² / tr(C²)`, is the participation ratio. `[recall]`
- Isotonic and unimodal least squares by pooling adjacent violators. `[recall]`
- [Sameness on a budget](../observers/README.md), law 4: observers together separate at most the product of what each separates alone, and reach it only when independent. Section 4.7 is that law with a number on it.
