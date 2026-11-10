from functools import lru_cache
from uuid import UUID

from pydantic import EmailStr, PositiveInt, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Moodle Course Review"
    database_url: str = "sqlite+pysqlite:///:memory:"
    log_level: str = "INFO"
    extension_redirect_uris: str = ""
    bootstrap_admin_email: str | None = None
    bootstrap_admin_display_name: str = "Administrator"
    bootstrap_admin_password: str | None = None
    dashboard_session_hours: int = 8
    attachment_storage_dir: str = "var/attachments"
    attachment_max_bytes: PositiveInt = 10 * 1024 * 1024
    notification_pilot_course_id: UUID | None = None
    notification_pilot_recipient: str | None = None
    notification_pilot_sender: str | None = None
    notification_pilot_url: str | None = None
    notification_pilot_preview_comment_id: UUID | None = None
    reviewer_access_mail_secret: SecretStr | None = None
    reviewer_access_enabled: bool = False
    reviewer_access_learn_trial_email: EmailStr | None = None
    reviewer_access_admin_email: str | None = None
    reviewer_access_origin: str | None = None
    reviewer_access_sender: str | None = None

    @model_validator(mode="after")
    def distinct_email_access_modes(self):
        if self.reviewer_access_enabled and self.reviewer_access_learn_trial_email:
            raise ValueError("Choose scoped LEARN trial or global reviewer email access, not both")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
