# Sufficiency Heuristics

These are operating heuristics, not statistical guarantees.

## Binary Detection (`error_present`)

Minimum to start iterating:
- `gold`: 25 positives + 25 negatives
- `test`: 25 positives + 25 negatives

More stable for prompt promotion:
- `gold`: 50 positives + 50 negatives
- `test`: 50 positives + 50 negatives

Good enough for a first local release:
- 95% bootstrap CI half-width <= `0.05` on the primary metric

## Error Classes

Minimum to start taxonomy work:
- at least 15 labeled examples per class that the model is expected to predict

More stable target:
- 30 or more per class

If classes are sparse, merge or defer them rather than pretending they are learnable.

## Where To Add Labels

Add labels where one of these is true:
- bootstrap interval is still wide
- class balance is poor
- LLM and ML disagree
- a route condition is fragile around a boundary
- the user cares about a specific product segment that is underrepresented

## Helper Interpretation

Use `scripts/bootstrap_sufficiency.py` output like this:
- `half_width > 0.08`: too noisy, keep labeling
- `0.05 < half_width <= 0.08`: enough for rough iteration, not enough for confident promotion
- `half_width <= 0.05`: usually acceptable for local iteration and graph selection
- `half_width <= 0.03`: strong enough for tighter comparisons

Estimated required sample size is a scaling heuristic based on the current interval width; use it to size the next labeling batch, not as a formal proof.
