from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "revenue-ai-automation-suite"
    environment: str = "development"
    database_url: str = "sqlite:///./revenue_ai_automation_suite.db"
    crm_adapter_mode: str = "mock"
    hubspot_enabled: bool = False
    hubspot_access_token: str = ""
    hubspot_portal_id: str = ""
    hubspot_default_pipeline: str = ""
    hubspot_default_deal_stage: str = ""
    hubspot_owner_id: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
