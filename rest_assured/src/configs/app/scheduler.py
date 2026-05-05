from pydantic import BaseModel


class SchedulerConfig(BaseModel):
    refresh_interval: int = 30
