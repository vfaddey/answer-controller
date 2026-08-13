from pydantic import PositiveInt, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://answer:answer@localhost:5432/answer_controller"
    redis_url: str = "redis://localhost:6379/0"
    warning_seconds: PositiveInt = 60
    overdue_seconds: PositiveInt = 180
    sla_batch_size: PositiveInt = 100
    outbox_batch_size: PositiveInt = 50
    log_level: str = "INFO"

    @model_validator(mode="after")
    def validate_thresholds(self) -> "Settings":
        if self.warning_seconds >= self.overdue_seconds:
            msg = "WARNING_SECONDS must be less than OVERDUE_SECONDS"
            raise ValueError(msg)
        return self
