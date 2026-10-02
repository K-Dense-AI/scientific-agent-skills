# Choosing and Reporting a Split

The split decides which question a metric answers. Two models can be compared
on the same table, with the same metric, and differ by twenty points purely
because one was scored on a random split and the other on a scaffold split. The
number is not wrong in either case; the *claim* is, whenever the split is not
named.

## What each split answers

| Split | Question it answers | When it is the honest choice |
| --- | --- | --- |
| **Random** | Can the model rank new *compounds* of chemistry it has already seen? | Analogue triage inside an existing series; interpolating a measured series |
| **Scaffold** (Bemis-Murcko) | Can the model rank *new chemotypes*? | Almost every published claim, and every claim about a novel series |
| **Time** | Would this have worked on the compounds discovered after training? | Prospective claims, and any model whose training data has a date |
| **Group / series** | Can the model handle a compound it has not already memorized? | Tables with repeat measurements, congeneric series, or a cluster column |

Random splitting is not a weaker version of the others; it is a different
experiment. Keep it in the report as a reference point -- the gap between the
random and scaffold numbers is itself the most informative single quantity in
the comparison, because it measures how much of the apparent performance came
from recognizable chemistry.

## Why a scaffold split usually scores worse

A random split puts molecules from the same series on both sides. The model
learns "this ring system tends to be potent" and reproduces it on the test side.
That is memorization of a chemotype, not prediction, and it is invisible in the
metric.

`split_compare.py` reports the mechanism alongside the score: how many test
compounds have a near-identical training neighbour, and how many test scaffolds
also occur in training. A scaffold split should show zero shared scaffolds --
if it does not, the split is not doing what its name says.

## Implementing a scaffold split

1. Compute the Bemis-Murcko scaffold of every compound.
2. Group compounds by scaffold, so a scaffold is never divided.
3. Assign whole groups to the test side, usually largest first, until the test
   fraction is reached.

Assigning whole groups is the part that is easy to get wrong. Splitting a large
scaffold group across both sides reintroduces exactly the leakage the split was
meant to remove, and it will not show up as an error -- only as a better score.

Two consequences worth stating in a report:

- **Acyclic compounds have an empty scaffold** and therefore all group together.
  In a table that is mostly acyclic (fragments, lipids, short peptides) the
  scaffold split degenerates. Check the scaffold distribution before trusting it.
- **The test fraction is approximate.** Whole groups are moved, so the achieved
  fraction can miss the target by a group's size. Report the actual sizes.

`split_compare.py` refuses to run when every row shares one scaffold, rather than
silently producing a split that holds nothing out.

## Group splits

Use a group split when the same compound appears more than once, since a random
split would place the repeat measurement of a training compound in the test set
and score the model on a molecule it has already seen. `split_compare.py`
collapses duplicate structures before splitting and reports how many it
collapsed; the count belongs in the report, because the effective dataset is
smaller than the file.

A cluster column, a series identifier, or an InChIKey all work as the grouping
key.

## Time splits

Order by the date column and hold out the most recent fraction. Check two things
before believing the result:

- **The column is actually chronological.** A `year` column that was filled in
  from a lookup table, or a `date` that is the database insertion time rather
  than the assay date, produces a split that looks temporal and is not.
- **The activity distribution has not drifted.** If the later compounds are
  systematically more potent -- which happens, because medicinal chemistry
  improves compounds over time -- a regression model will look worse for reasons
  that have nothing to do with its chemistry.

## Reporting rules

- **Name the split next to every number.** "RMSE 0.36" is not a result.
  "RMSE 0.36 (random split), 1.28 (scaffold split)" is.
- **Report the sizes.** Number of compounds per side, and number of distinct
  scaffolds per side. A scaffold split with four test scaffolds is four
  independent draws, whatever the compound count says.
- **Report the seed.** Run at least three seeds and give the range. On tables of
  a few hundred compounds the seed-to-seed spread is often comparable to the
  difference between two models, which means the difference is not evidence.
- **Say which side is which** when the split is not symmetric in size.
