from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Coroutine


@dataclass
class SchedulerTask:
    id: str
    expires_at: datetime
    task: Callable | Coroutine
    replace: bool = False

    def __lt__(self, other):
        return self.expires_at < other.expires_at
