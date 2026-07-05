import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.models.lead_scoring import LeadScoringRequest  # noqa: E402
from app.services.lead_scoring import score_lead  # noqa: E402


def load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    leads = load_json(REPO_ROOT / "sample-data" / "leads.json")
    expected_results = load_json(
        REPO_ROOT / "sample-data" / "lead-scoring-expected-results.json"
    )
    expected_by_id = {result["lead_id"]: result for result in expected_results}

    passed = 0
    failed = 0

    for lead_data in leads:
        lead = LeadScoringRequest(**lead_data)
        result = score_lead(lead)
        expected = expected_by_id[result.lead_id]
        failures = checked_field_failures(result, expected)

        if not failures:
            passed += 1
            print(
                f"PASS {result.lead_id}: "
                f"score={result.lead_score}, "
                f"priority={result.priority}, "
                f"confidence={result.confidence}, "
                f"urgency={result.urgency}, "
                f"human_review_required={result.human_review_required}"
            )
        else:
            failed += 1
            print(f"FAIL {result.lead_id}:")
            for failure in failures:
                print(f"  - {failure}")
            print(
                "  info: "
                f"pain_points={result.pain_points}, "
                f"recommended_route={result.recommended_route}, "
                f"next_best_action={result.next_best_action}, "
                f"reasoning={result.reasoning}"
            )

    print(f"Summary: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


def checked_field_failures(result, expected: dict) -> list[str]:
    failures: list[str] = []

    exact_fields = [
        "priority",
        "human_review_required",
        "confidence",
        "urgency",
    ]

    for field in exact_fields:
        actual_value = getattr(result, field)
        expected_value = expected[field]
        if actual_value != expected_value:
            failures.append(
                f"{field}: expected {expected_value!r}, got {actual_value!r}"
            )

    expected_score = expected["lead_score"]
    score_delta = abs(result.lead_score - expected_score)
    if score_delta > 10:
        failures.append(
            "lead_score: "
            f"expected within 10 points of {expected_score}, "
            f"got {result.lead_score} (delta {score_delta})"
        )

    return failures


if __name__ == "__main__":
    raise SystemExit(main())
