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
    "flagmissing",
    "createa",
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
        result = summarize_meeting(MeetingSummaryRequest(**meeting_data))
        expected = expected_by_id[result.meeting_id]

        failures = []

        for field in FIELDS_TO_CHECK:
            actual_value = getattr(result, field)
            expected_value = expected[field]

            if actual_value != expected_value:
                failures.append(
                    f"{field}: expected={expected_value}, actual={actual_value}"
                )

        if not result.recommended_actions:
            failures.append("recommended_actions: expected at least one action")

        for action in result.recommended_actions:
            for bad_fragment in BAD_DESCRIPTION_FRAGMENTS:
                if bad_fragment in action.description:
                    failures.append(
                        "dirty action description\n"
                        f"  action_type={action.action_type}\n"
                        f"  bad_fragment={bad_fragment}\n"
                        f"  description={action.description}"
                    )

        for action in result.recommended_actions:
            description_lower = action.description.lower()

            for bad_fragment in BAD_DESCRIPTION_FRAGMENTS:
                if bad_fragment in description_lower:
                    failures.append(
                        "dirty action description\n"
                        f"  action_type={action.action_type}\n"
                        f"  bad_fragment={bad_fragment}\n"
                        f"  description={action.description}"
                    )

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
            description_lower = action.description.lower()

            bad_fragments = [
                "thereview",
                "reviewqueue",
                "flagmissing",
                "createa",
                "arep",
                "nextsteps",
                "agreednext",
                "aretoo",
                "actionsto",
                "withrevenue",
            ]

            for bad_fragment in bad_fragments:
                if bad_fragment in description_lower:
                    print(f"FAIL {result.meeting_id}: dirty action description")
                    print(f"  action_type={action.action_type}")
                    print(f"  bad_fragment={bad_fragment}")
                    print(f"  description={action.description}")
                    raise SystemExit(1)

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
