from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Coroutine


@dataclass
class SchedulerTask:
    expires_at: datetime
    task: Callable[..., None] | Coroutine

    def __lt__(self, other):
        return self.expires_at < other.expires_at
