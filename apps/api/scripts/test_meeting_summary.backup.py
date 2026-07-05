from pathlib import Path
import json
import sys

API_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(API_ROOT))

from app.models.meeting_summary import MeetingSummaryRequest  # noqa: E402
from app.services.meeting_summary import summarize_meeting  # noqa: E402


BAD_DESCRIPTION_FRAGMENTS = [
    "thereview",
    "reviewqueue",
    "Flagmissing",
    "Createa",
    "arep",
    "nextsteps",
    "agreednext",
    "aretoo",
    "actionsto",
    "withrevenue",
]


FIELDS_TO_CHECK = [
    "confidence",
    "human_review_required",
    "needs_more_info",
    "proposal_needed",
    "deal_stage_recommendation",
]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_dirty_description_failures(actions) -> list[str]:
    failures: list[str] = []

    for action in actions:
        for bad_fragment in BAD_DESCRIPTION_FRAGMENTS:
            if bad_fragment in action.description:
                failures.append(
                    "\n".join(
                        [
                            "dirty action description",
                            f"  action_type={action.action_type}",
                            f"  bad_fragment={bad_fragment}",
                            f"  description={action.description}",
                        ]
                    )
                )

    return failures


def main() -> None:
    meetings = load_json(PROJECT_ROOT / "sample-data" / "meeting-transcripts.json")
    expected_results = load_json(
        PROJECT_ROOT / "sample-data" / "meeting-summary-expected-results.json"
    )

    expected_by_id = {
        expected["meeting_id"]: expected for expected in expected_results
    }

    passed = 0
    failed = 0

    for meeting_data in meetings:
        meeting = MeetingSummaryRequest(**meeting_data)
        result = summarize_meeting(meeting)
        expected = expected_by_id[result.meeting_id]

        failures: list[str] = []

        for field in FIELDS_TO_CHECK:
            actual_value = getattr(result, field)
            expected_value = expected[field]

            if actual_value != expected_value:
                failures.append(
                    f"{field}: expected={expected_value}, actual={actual_value}"
                )

        if not result.recommended_actions:
            failures.append("recommended_actions: expected at least one action")

        failures.extend(find_dirty_description_failures(result.recommended_actions))

        if failures:
            failed += 1
            print(
                f"FAIL {result.meeting_id}: "
                f"confidence={result.confidence}, "
                f"human_review_required={result.human_review_required}, "
                f"needs_more_info={result.needs_more_info}, "
                f"proposal_needed={result.proposal_needed}, "
                f"deal_stage_recommendation={result.deal_stage_recommendation}"
            )

            for failure in failures:
                print(f"  - {failure}")
        else:
            passed += 1
            print(
                f"PASS {result.meeting_id}: "
                f"confidence={result.confidence}, "
                f"human_review_required={result.human_review_required}, "
                f"needs_more_info={result.needs_more_info}, "
                f"proposal_needed={result.proposal_needed}, "
                f"deal_stage_recommendation={result.deal_stage_recommendation}"
            )

        print("  recommended_actions:")
        for action in result.recommended_actions:
            print(
                f"    - {action.action_type} "
                f"({action.automation_status}, due={action.due}): "
                f"{action.description}"
            )

    print(f"Summary: {passed} passed, {failed} failed")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
