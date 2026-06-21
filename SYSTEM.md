# Blind Wit Loop

## The Simple Mental Model

The workflow has three responsibilities:

1. **Creator invents.** It sees the sentence beginning but not the scoring criteria.
2. **Evaluator scores.** It sees one candidate and the criteria but not the current winner or its score.
3. **Finalizer compares.** A deterministic script compares numbers and updates the files. No model chooses the winner.

The workflow is easier to understand as three separate flows.

Generated runtime files such as `creator/completion.txt`, `judge/candidate.json`, `judge/criteria.md`, `judge/evaluation.json`, and `.wit/pending/*.json` are created by the helper scripts during a run. They may not exist while the loop is idle.

## Automations

This repository expects two cron automations with the following IDs, prompts, and working directories.

### Creator

```text
id:                     wit-creator
name:                   Wit Creator
kind:                   cron
status:                 ACTIVE
schedule:               every hour at :00
timezone:               Europe/Tallinn
working directory:      /Users/erikuus/dev/wit-loop/creator
execution environment:  local
model:                  gpt-5.4
reasoning effort:       high
```

Creator prompt:

```text
Run exactly one blind wit creation iteration. First run `../bin/prepare-creator`. Read only `input.md` in the current working directory. Do not inspect parent directories or any criteria, scores, incumbent, state, evaluator files, or previous candidates; the only permitted parent-directory actions are invoking the exact helper commands named here. Generate exactly one original second half that makes the supplied beginning as witty as possible using your own creative judgment. Write only the second half to `completion.txt`; do not repeat the supplied beginning and do not explain or score it. Then run `../bin/submit-candidate completion.txt`. Stop after the helper confirms submission.
```

### Evaluator

```text
id:                     wit-evaluator
name:                   Wit Evaluator
kind:                   cron
status:                 ACTIVE
schedule:               every hour at :15
timezone:               Europe/Tallinn
working directory:      /Users/erikuus/dev/wit-loop/judge
execution environment:  local
model:                  gpt-5.4
reasoning effort:       high
```

Evaluator prompt:

```text
Run exactly one blind wit evaluation iteration. First run `../bin/prepare-evaluation`. If it reports that no candidate is pending, stop without creating or changing files. Read only `candidate.json` and `criteria.md` in the current working directory. Do not inspect parent directories or any incumbent, best score, state, creator files, previous candidates, or previous evaluations; the only permitted parent-directory actions are invoking the exact helper commands named here. Evaluate the candidate as an absolute judgment under `criteria.md`, without comparison to any other sentence. Write `evaluation.json` with exactly these top-level fields: `candidate_id`, `raw_scores`, `final_score`, and `rationale`. Copy the ID from `candidate.json`. `raw_scores` must contain exactly `conceptual_reversal_and_logic`, `precision_of_the_pivot`, `compression_and_force`, `quotable_shape`, `originality_without_strain`, `human_truth_carried_by_wit`, and `elegance`, each scored from 0 to 5 in half-point increments. Compute the weighted total using the rubric weights, clamp to 0–100, and round to the nearest whole number. Emotional tone, including vulnerability, neediness, bleakness, confidence, or self-exposure, must neither add nor subtract points by itself. Keep the rationale concise and independent of any imagined incumbent. Then run `../bin/finalize-evaluation`. Do not inspect its effects or report whether the candidate won.
```

### Creation

```text
Creator reads:       input.md
Creator writes:      creator/completion.txt
Submit script creates: .wit/pending/ID.json
```

Example `.wit/pending/20260620T140000Z-a1b2c3d4.json`:

```json
{
  "id": "20260620T140000Z-a1b2c3d4",
  "input": "I can resist everything except",
  "completion": "temptation.",
  "sentence": "I can resist everything except temptation."
}
```

### Evaluation

```text
Candidate is moved:  .wit/pending/ID.json -> judge/candidate.json
Rubric is copied:    criteria.md -> judge/criteria.md
Evaluator writes:    judge/evaluation.json
```

Example `judge/evaluation.json`:

```json
{
  "candidate_id": "20260620T140000Z-a1b2c3d4",
  "raw_scores": {
    "conceptual_reversal_and_logic": 5,
    "precision_of_the_pivot": 5,
    "compression_and_force": 5,
    "quotable_shape": 5,
    "originality_without_strain": 5,
    "human_truth_carried_by_wit": 5,
    "elegance": 5
  },
  "final_score": 100,
  "rationale": "The ending creates a perfect logical paradox with maximum precision and compression."
}
```

Raw scores range from `0` to `5` and may use half-points. The finalizer recalculates the weighted total and rejects an inconsistent `final_score`.

### Decision

```text
Finalizer reads:     judge/candidate.json
                     judge/evaluation.json
                     .wit/state.json

If candidate wins:   update best.md and .wit/state.json

If candidate loses
or ties:             leave best.md and .wit/state.json unchanged

Finalizer archives:  .wit/evaluations/ID.json
Finalizer deletes:   the three temporary judge files
```

The Finalizer is deterministic code. It validates the score, recalculates the weighted total, and only then reads the hidden incumbent state.

### Example State Before the Decision

In loop 2, `.wit/state.json` describes the winner from loop 1:

```json
{
  "schema_version": 1,
  "input": "I can resist everything except",
  "criteria_sha256": "40b3e6d4e9df841df5105e0279e32f7b249150048266a406669013e893dbab4a",
  "best_score": 75,
  "best_candidate_id": "previous-candidate-id",
  "updated_at": "2026-06-20T13:15:00+00:00"
}
```

`best.md` contains:

```text
I can resist everything except coffee.
```

The new candidate scored `100`, so it wins. The Finalizer changes `best.md` to:

```text
I can resist everything except temptation.
```

It also changes `.wit/state.json` to store the new score and candidate ID.

### Example Evaluation Archive

The Finalizer creates `.wit/evaluations/20260620T140000Z-a1b2c3d4.json`:

```json
{
  "schema_version": 1,
  "candidate": {
    "id": "20260620T140000Z-a1b2c3d4",
    "input": "I can resist everything except",
    "completion": "temptation.",
    "sentence": "I can resist everything except temptation."
  },
  "evaluation": {
    "candidate_id": "20260620T140000Z-a1b2c3d4",
    "criteria_sha256": "40b3e6d4e9df841df5105e0279e32f7b249150048266a406669013e893dbab4a",
    "raw_scores": {
      "conceptual_reversal_and_logic": 5,
      "precision_of_the_pivot": 5,
      "compression_and_force": 5,
      "quotable_shape": 5,
      "originality_without_strain": 5,
      "human_truth_carried_by_wit": 5,
      "elegance": 5
    },
    "final_score": 100,
    "rationale": "The ending creates a perfect logical paradox with maximum precision and compression."
  },
  "decision": {
    "outcome": "winner",
    "reason": "Scored 100/100, above the incumbent's 75/100.",
    "incumbent_before": {
      "candidate_id": "previous-candidate-id",
      "score": 75,
      "sentence": "I can resist everything except coffee."
    }
  },
  "finalized_at": "2026-06-20T14:15:00+00:00"
}
```

This single archive explains the complete decision: what was generated, how it was scored, whether it won, why it won, and what it replaced.

For a losing candidate, the archive records `"outcome": "loser"` and the incumbent it failed to beat. For a tie, it records `"outcome": "tie"`; `best.md` and `.wit/state.json` remain unchanged.

After writing the archive, the Finalizer deletes:

```text
judge/candidate.json
judge/criteria.md
judge/evaluation.json
```

The judge workspace is empty and ready for the next loop.

## Validation

Run the test suite from the repository root with:

```text
python3 -m unittest discover -s tests -q
```

## Exceptional Cases

- If `.wit/pending/` is empty, the Evaluator stops without scoring anything.
- If the input changes before finalization, the archive records the candidate as stale and it cannot become the winner.
- If the rubric changes during evaluation, finalization refuses the result. The temporary files are discarded automatically on the next Evaluator run.
- If a Creator or Evaluator run is interrupted, the next scheduled run cleans its temporary workspace and continues with the queue. No manual recovery is required.

## Isolation Boundary

The Creator model receives only the input. The Evaluator model receives only one candidate and the rubric. Only deterministic helper scripts access the queue and hidden competition state.

This is strict cognitive isolation enforced by separate workspaces and automation instructions. It is not an operating-system security boundary because both automations run under the same local user account.
