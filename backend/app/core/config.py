import json
from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WordPressSiteConfig(BaseModel):
    name: str
    base_url: str
    username: str | None = None
    application_password: str | None = None


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "Marketing AI Hub Backend"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    public_backend_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:8100"
    api_prefix: str = "/api"
    oauth_storage_file: str = "storage/oauth_connections.json"
    oauth_keys_worksheet: str = "key"
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:8100",
            "http://127.0.0.1:8100",
            "http://localhost:4200",
            "http://127.0.0.1:4200",
        ]
    )
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    google_sheet_id: str = "your-google-sheet-id"
    google_sheet_worksheet: str = "social_overview"
    sync_interval_minutes: int = 60
    google_api_key: str | None = None
    google_service_account_email: str | None = None
    google_service_account_file: str | None = None
    google_service_account_json: str | None = None
    wordpress_posts_worksheet: str = "Post_web"
    daily_report_worksheet: str = "reportday"
    google_search_console_site_url: str | None = None
    google_analytics_property_id: str | None = None
    google_analytics_property_ids_json: str | None = None
    facebook_worksheet: str = "facebook"
    facebook_app_id: str | None = None
    facebook_app_secret: str | None = None
    facebook_access_token: str | None = None
    facebook_verify_token: str | None = None
    facebook_page_ids_json: str | None = None
    linkedin_worksheet: str = "linkedin"
    linkedin_api_version: str = "202601"
    linkedin_client_id: str | None = None
    linkedin_client_secret: str | None = None
    linkedin_access_token: str | None = None
    linkedin_organization_id: str | None = None
    linkedin_organization_ids_json: str | None = None
    youtube_worksheet: str = "youtube"
    youtube_api_key: str | None = None
    youtube_client_id: str | None = None
    youtube_client_secret: str | None = None
    youtube_refresh_token: str | None = None
    youtube_channel_id: str | None = None
    youtube_channel_ids_json: str | None = None
    tiktok_worksheet: str = "tiktok"
    tiktok_client_key: str | None = None
    tiktok_client_secret: str | None = None
    tiktok_access_token: str | None = None
    tiktok_open_id: str | None = None
    wordpress_sites_json: str | None = None
    wordpress_base_url: str | None = None
    wordpress_username: str | None = None
    wordpress_application_password: str | None = None
    hubspot_access_token: str | None = None
    mailchimp_api_key: str | None = None
    mailchimp_server_prefix: str | None = None
    zapier_webhook_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def get_wordpress_sites(self) -> list[WordPressSiteConfig]:
        if self.wordpress_sites_json and self.wordpress_sites_json.strip():
            data = json.loads(self.wordpress_sites_json)
            if not isinstance(data, list):
                raise ValueError("WORDPRESS_SITES_JSON must be a JSON array.")
            return [WordPressSiteConfig.model_validate(item) for item in data]

        if self.wordpress_base_url and self.wordpress_base_url.strip():
            return [
                WordPressSiteConfig(
                    name="Primary WordPress Site",
                    base_url=self.wordpress_base_url,
                    username=self.wordpress_username,
                    application_password=self.wordpress_application_password,
                )
            ]

        return []

    def get_google_analytics_property_ids(self) -> list[str]:
        if self.google_analytics_property_ids_json and self.google_analytics_property_ids_json.strip():
            data = json.loads(self.google_analytics_property_ids_json)
            if not isinstance(data, list):
                raise ValueError("GOOGLE_ANALYTICS_PROPERTY_IDS_JSON must be a JSON array.")
            return [str(item).strip() for item in data if str(item).strip()]

        if self.google_analytics_property_id and self.google_analytics_property_id.strip():
            return [self.google_analytics_property_id.strip()]

        return []

    def get_facebook_page_ids(self) -> list[str]:
        if self.facebook_page_ids_json and self.facebook_page_ids_json.strip():
            data = json.loads(self.facebook_page_ids_json)
            if not isinstance(data, list):
                raise ValueError("FACEBOOK_PAGE_IDS_JSON must be a JSON array.")
            return [str(item).strip() for item in data if str(item).strip()]

        return []

    def get_linkedin_organization_ids(self) -> list[str]:
        if self.linkedin_organization_ids_json and self.linkedin_organization_ids_json.strip():
            data = json.loads(self.linkedin_organization_ids_json)
            if not isinstance(data, list):
                raise ValueError("LINKEDIN_ORGANIZATION_IDS_JSON must be a JSON array.")
            return [str(item).strip() for item in data if str(item).strip()]

        if self.linkedin_organization_id and self.linkedin_organization_id.strip():
            return [self.linkedin_organization_id.strip()]

        return []

    def get_youtube_channel_ids(self) -> list[str]:
        if self.youtube_channel_ids_json and self.youtube_channel_ids_json.strip():
            data = json.loads(self.youtube_channel_ids_json)
            if not isinstance(data, list):
                raise ValueError("YOUTUBE_CHANNEL_IDS_JSON must be a JSON array.")
            return [str(item).strip() for item in data if str(item).strip()]

        if self.youtube_channel_id and self.youtube_channel_id.strip():
            return [self.youtube_channel_id.strip()]

        return []


@lru_cache
def get_settings() -> Settings:
    return Settings()
