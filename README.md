# Blind Wit Loop

`wit-loop` is a small Python-driven workflow for iterating toward the strongest second half of a sentence in the style of classic wit.

It separates the work into three blind stages:

1. A creator sees only the sentence beginning and writes one completion.
2. An evaluator sees only the candidate and the scoring rubric and assigns an absolute score.
3. A deterministic finalizer validates the score, compares it against the incumbent, and updates the winner.

No model compares candidates directly. The winning line changes only when the deterministic code accepts a strictly higher score.

## Repository Structure

- `input.md`: the sentence beginning the creator must complete
- `criteria.md`: the scoring rubric for absolute evaluation
- `best.md`: the current winning full sentence
- `bin/prepare-creator`: copies the current prompt into the isolated creator workspace
- `bin/submit-candidate`: turns one completion into a queued candidate
- `bin/prepare-evaluation`: moves the oldest queued candidate into the isolated judge workspace
- `bin/finalize-evaluation`: validates scoring and updates the incumbent deterministically
- `tests/test_wit_loop.py`: end-to-end tests for queueing, evaluation, replacement, ties, stale input, and rubric resets
- `.wit/state.json`: current competition state
- `.wit/evaluations/`: archived candidate evaluations and decisions

## How It Works

The loop is designed to preserve blindness:

- The creator does not see the rubric, score history, or incumbent.
- The evaluator does not see the incumbent or any previous candidates.
- The finalizer is plain code, not a model judgment.

This means the system optimizes by repeated independent attempts rather than by direct model-to-model comparison.

## Local Workflow

Run one manual iteration from the repository root:

```bash
bin/prepare-creator
```

Read `creator/input.md`, write a completion to `creator/completion.txt`, then submit it:

```bash
bin/submit-candidate creator/completion.txt
```

Move the oldest pending candidate into the isolated judge workspace:

```bash
bin/prepare-evaluation
```

Create `judge/evaluation.json` with these top-level fields:

- `candidate_id`
- `raw_scores`
- `final_score`
- `rationale`

Then finalize the evaluation:

```bash
bin/finalize-evaluation
```

The finalizer will:

- recompute the weighted score
- reject malformed or inconsistent evaluations
- compare against the incumbent only after validation
- update `best.md` and `.wit/state.json` only on a strict win
- archive the full decision in `.wit/evaluations/`

## Testing

Run the test suite from the repository root:

```bash
python3 -m unittest discover -s tests -q
```

## Automation Contract

The repository is intended to support two recurring automations:

- a creator run at the top of the hour
- an evaluator run at `:15`

The exact prompts and working-directory setup live in `SYSTEM.md`.

## Notes

- Runtime workspace files such as `creator/completion.txt` and `judge/evaluation.json` are ignored by git.
- The archived evaluation history in `.wit/evaluations/` and the current state in `.wit/state.json` can be kept in the repository if you want the competition history versioned.
