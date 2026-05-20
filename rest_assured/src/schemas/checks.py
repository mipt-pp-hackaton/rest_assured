from datetime import datetime
from typing import Protocol


class CheckResultProtocol(Protocol):
    checked_at: datetime
    is_up: bool
