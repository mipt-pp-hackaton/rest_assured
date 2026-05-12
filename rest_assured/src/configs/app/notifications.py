from pydantic import BaseModel


class NotificationsConfig(BaseModel):
    enabled: bool = True
    reminder_cooldown_minutes: int = 30
    include_runbook_link: bool = False
