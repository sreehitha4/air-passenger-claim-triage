
import json
from pathlib import Path
from typing import Any

from agents.graph import claim_graph
from app.models import PassengerClaim


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_FILE = PROJECT_ROOT / "evaluation" / "claim_triage_eval.json"
RESULTS_FILE = PROJECT_ROOT / "evaluation" / "claim_triage_eval_results.json"


def load_dataset(path: Path) -> dict[str, Any]:
    """Load and validate the evaluation dataset structure."""

    if not path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    if not isinstance(dataset.get("base_claim"), dict):
        raise ValueError("Dataset must contain a base_claim object.")

    scenarios = dataset.get("scenarios")

    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("Dataset must contain a non-empty scenarios list.")

    scenario_ids = [scenario.get("id") for scenario in scenarios]

    if any(not isinstance(item, str) or not item for item in scenario_ids):
        raise ValueError("Every scenario must have a non-empty string ID.")

    if len(scenario_ids) != len(set(scenario_ids)):
        raise ValueError("Scenario IDs must be unique.")

    return dataset


def evaluate_scenario(
    base_claim: dict[str, Any],
    scenario: dict[str, Any],
) -> dict[str, Any]:
    """Run one scenario and compare selected outputs to expectations."""

    scenario_id = scenario["id"]
    claim_data = {**base_claim, **scenario.get("overrides", {})}
    expected = scenario.get("expected", {})
    checks = []
    actual: dict[str, Any] = {}

    try:
        # Validate each input using the same schema as the API.
        claim = PassengerClaim.model_validate(claim_data)

        result = claim_graph.invoke({
            "claim": claim.model_dump(mode="json"),
            "retry_count": 0,
        })

        actual = {
            "next_action": result.get("next_action"),
            "missing_information": result.get("missing_information", []),
            "verification_status": result.get("verification_status"),
            "recommendation": result.get("recommendation"),
            "escalation_reason": result.get("escalation_reason"),
            "clause_assessment_count": len(
                result.get("clause_assessments", [])
            ),
        }

        for field in (
            "next_action",
            "missing_information",
            "verification_status",
        ):
            if field in expected:
                passed = actual[field] == expected[field]
                checks.append({
                    "field": field,
                    "passed": passed,
                    "expected": expected[field],
                    "actual": actual[field],
                })

        if expected.get("no_recommendation") is True:
            passed = actual["recommendation"] is None
            checks.append({
                "field": "no_recommendation",
                "passed": passed,
                "expected": None,
                "actual": actual["recommendation"],
            })

    except Exception as exc:
        actual = {
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        checks.append({
            "field": "execution",
            "passed": False,
            "expected": "Scenario executes without an exception",
            "actual": actual,
        })

    return {
        "scenario_id": scenario_id,
        "description": scenario.get("description", ""),
        "passed": bool(checks) and all(check["passed"] for check in checks),
        "checks": checks,
        "actual": actual,
    }


def main() -> None:
    dataset = load_dataset(DATASET_FILE)
    scenarios = dataset["scenarios"]
    results = [
        evaluate_scenario(dataset["base_claim"], scenario)
        for scenario in scenarios
    ]

    passed = sum(result["passed"] for result in results)
    failed = len(results) - passed

    report = {
        "evaluation_version": dataset.get("evaluation_version", 1),
        "dataset": DATASET_FILE.name,
        "scenario_count": len(results),
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / len(results), 4),
        "results": results,
    }

    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with RESULTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    print(f"Scenarios evaluated: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Pass rate: {report['pass_rate']:.1%}")
    print(f"Detailed report: {RESULTS_FILE}")

    if failed:
        print("\nScenario mismatches:")
        for result in results:
            if not result["passed"]:
                print(f"\n{result['scenario_id']}: {result['description']}")
                for check in result["checks"]:
                    if not check["passed"]:
                        print(
                            f"  {check['field']}: "
                            f"expected={check['expected']!r}, "
                            f"actual={check['actual']!r}"
                        )


if __name__ == "__main__":
    main()
