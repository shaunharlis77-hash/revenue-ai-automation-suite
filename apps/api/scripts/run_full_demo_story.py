import argparse
import sys
from pathlib import Path


API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.services.demo_lifecycle import run_full_demo_story  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the full synthetic Revenue AI demo story."
    )
    parser.add_argument(
        "--reset-demo",
        action="store_true",
        help="Reset local persistence before running the demo. Local/demo only.",
    )
    args = parser.parse_args()

    result = run_full_demo_story(reset_demo=args.reset_demo)
    print("Full demo story completed.")
    print(f"demo_run_id={result.demo_run_id}")
    print(f"crm_record_id={result.crm_record_id}")
    print(f"lead_score={result.lead_score}")
    print(f"priority={result.priority}")
    print(f"route={result.route}")
    print(f"hubspot_contact_id={result.hubspot_contact_id}")
    print(f"hubspot_company_id={result.hubspot_company_id}")
    print(f"hubspot_deal_id={result.hubspot_deal_id}")
    print(f"meeting_summary_status={result.meeting_summary_status}")
    print(f"follow_up_review_item_id={result.follow_up_review_item_id}")
    print(f"follow_up_approval_status={result.follow_up_approval_status}")
    print(f"follow_up_outcome={result.follow_up_outcome}")
    print(f"proposal_review_item_id={result.proposal_review_item_id}")
    print(f"proposal_status={result.proposal_status}")
    print(f"hygiene_status={result.hygiene_status}")
    print(f"audit_events_created={result.audit_events_created}")
    print(f"workflow_step_events_created={result.workflow_step_events_created}")
    print(f"review_items_created={result.review_items_created}")
    print(f"notifications_sent_or_queued={result.notifications_sent_or_queued}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
