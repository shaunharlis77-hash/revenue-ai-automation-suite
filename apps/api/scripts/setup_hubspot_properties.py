import sys
from pathlib import Path


API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.services.hubspot_adapter import ensure_custom_properties, get_hubspot_status  # noqa: E402


def main() -> int:
    status = get_hubspot_status()
    print(f"adapter_mode={status.adapter_mode}")
    print(f"hubspot_enabled={status.hubspot_enabled}")
    print(f"token_configured={status.token_configured}")
    print(f"status={status.status}")

    if status.status != "ready":
        print("HubSpot property setup skipped because HubSpot is not ready.")
        return 0

    result = ensure_custom_properties()
    print(f"setup_status={result.status}")
    print(f"created={len(result.created)}")
    print(f"skipped_existing={len(result.skipped_existing)}")
    print(f"failed={len(result.failed)}")
    if result.failed:
        print("failed_properties=" + ", ".join(result.failed))
        if result.failed_details:
            print("failed_details:")
            for detail in result.failed_details:
                print(f"- {detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
