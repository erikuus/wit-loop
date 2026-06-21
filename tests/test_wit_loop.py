from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1]
COMPONENTS = [
    "conceptual_reversal_and_logic",
    "precision_of_the_pivot",
    "compression_and_force",
    "quotable_shape",
    "originality_without_strain",
    "human_truth_carried_by_wit",
    "elegance",
]
WEIGHTS = [5, 4, 3, 3, 2, 2, 1]


def raw_scores_for(score: int) -> dict[str, float]:
    possibilities: dict[int, list[int]] = {0: []}
    for weight in WEIGHTS:
        updated: dict[int, list[int]] = {}
        for total, values in possibilities.items():
            for half_units in range(11):
                updated.setdefault(total + half_units * weight, values + [half_units])
        possibilities = updated
    values = possibilities[score * 2]
    return {name: value / 2 for name, value in zip(COMPONENTS, values)}


class WitLoopTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(SOURCE / "bin", self.root / "bin")
        (self.root / "creator").mkdir()
        (self.root / "judge").mkdir()
        for directory in ("pending", "evaluations"):
            (self.root / ".wit" / directory).mkdir(parents=True, exist_ok=True)
        (self.root / "input.md").write_text("Life is short,\n", encoding="utf-8")
        (self.root / "criteria.md").write_text("test rubric\n", encoding="utf-8")
        (self.root / "best.md").write_text("", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_script(self, name: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.root / "bin" / name), *args],
            cwd=self.root,
            check=check,
            text=True,
            capture_output=True,
        )

    def submit(self, completion: str) -> None:
        self.run_script("prepare-creator")
        path = self.root / "creator" / "completion.txt"
        path.write_text(completion + "\n", encoding="utf-8")
        self.run_script("submit-candidate", str(path))
        self.run_script("prepare-evaluation")

    def evaluate(self, score: int, candidate_id: str | None = None) -> subprocess.CompletedProcess[str]:
        candidate = json.loads((self.root / "judge" / "candidate.json").read_text(encoding="utf-8"))
        evaluation = {
            "candidate_id": candidate_id or candidate["id"],
            "raw_scores": raw_scores_for(score),
            "final_score": score,
            "rationale": "Blind absolute evaluation.",
        }
        (self.root / "judge" / "evaluation.json").write_text(
            json.dumps(evaluation), encoding="utf-8"
        )
        return self.run_script("finalize-evaluation", check=False)

    def decisions(self) -> list[dict]:
        archives = sorted((self.root / ".wit" / "evaluations").glob("*.json"))
        return [json.loads(path.read_text(encoding="utf-8"))["decision"] for path in archives]

    def test_first_candidate_becomes_incumbent(self) -> None:
        self.submit("so invoice accordingly.")
        result = self.evaluate(25)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "best.md").read_text(encoding="utf-8").strip(),
                         "Life is short, so invoice accordingly.")
        state = json.loads((self.root / ".wit" / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["best_score"], 25)
        self.assertEqual(state["input"], "Life is short,")
        self.assertIn("criteria_sha256", state)

    def test_higher_replaces_lower_loses_and_tie_preserves(self) -> None:
        self.submit("so invoice accordingly.")
        self.assertEqual(self.evaluate(25).returncode, 0)

        self.submit("but meetings are longer.")
        self.assertEqual(self.evaluate(40).returncode, 0)
        winner = (self.root / "best.md").read_text(encoding="utf-8")

        self.submit("and poorly punctuated.")
        self.assertEqual(self.evaluate(20).returncode, 0)
        self.submit("unless it is a meeting.")
        self.assertEqual(self.evaluate(40).returncode, 0)

        self.assertEqual((self.root / "best.md").read_text(encoding="utf-8"), winner)
        decisions = self.decisions()
        self.assertEqual([decision["outcome"] for decision in decisions],
                         ["winner", "winner", "loser", "tie"])
        self.assertEqual(decisions[1]["incumbent_before"]["score"], 25)
        self.assertIn("ties preserve the incumbent", decisions[3]["reason"])
        self.assertFalse((self.root / "log.md").exists())

    def test_malformed_score_cannot_change_state(self) -> None:
        self.submit("so invoice accordingly.")
        candidate = json.loads((self.root / "judge" / "candidate.json").read_text(encoding="utf-8"))
        result = self.evaluate(25, candidate_id=candidate["id"] + "-wrong")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / ".wit" / "state.json").exists())
        self.assertEqual((self.root / "best.md").read_text(encoding="utf-8"), "")

    def test_changed_input_makes_candidate_stale(self) -> None:
        self.submit("so invoice accordingly.")
        (self.root / "input.md").write_text("Time flies,\n", encoding="utf-8")
        result = self.evaluate(25)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / ".wit" / "state.json").exists())
        self.assertEqual(self.decisions()[0]["outcome"], "stale")

    def test_changed_rubric_resets_incumbent_score(self) -> None:
        self.submit("so invoice accordingly.")
        self.assertEqual(self.evaluate(40).returncode, 0)
        (self.root / "criteria.md").write_text("revised rubric\n", encoding="utf-8")

        self.submit("and poorly punctuated.")
        self.assertEqual(self.evaluate(20).returncode, 0)

        state = json.loads((self.root / ".wit" / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["best_score"], 20)
        self.assertIn("scoring rubric changed", self.decisions()[1]["reason"])

    def test_failed_evaluation_does_not_block_next_candidate(self) -> None:
        self.submit("so invoice accordingly.")
        first = json.loads((self.root / "judge" / "candidate.json").read_text(encoding="utf-8"))

        completion = self.root / "creator" / "completion.txt"
        completion.write_text("but meetings are longer.\n", encoding="utf-8")
        self.run_script("submit-candidate", str(completion))
        self.run_script("prepare-evaluation")

        second = json.loads((self.root / "judge" / "candidate.json").read_text(encoding="utf-8"))
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(second["completion"], "but meetings are longer.")


if __name__ == "__main__":
    unittest.main()
