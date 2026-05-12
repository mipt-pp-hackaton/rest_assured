from pydantic import BaseModel


class SchedulerSettings(BaseModel):

    poll_interval_seconds: int = 5
    default_timeout_ms: int = 5000
