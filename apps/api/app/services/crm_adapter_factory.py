from app.config.settings import get_settings
from app.services import hubspot_adapter, mock_crm_adapter


def get_crm_adapter():
    settings = get_settings()
    adapter_mode = settings.crm_adapter_mode.strip().lower() or "mock"
    if adapter_mode == "hubspot" and settings.hubspot_enabled:
        return hubspot_adapter
    return mock_crm_adapter


def current_adapter_mode() -> str:
    settings = get_settings()
    adapter_mode = settings.crm_adapter_mode.strip().lower() or "mock"
    if adapter_mode == "hubspot" and settings.hubspot_enabled:
        return "hubspot"
    return "mock"
