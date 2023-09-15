from dataclasses import dataclass
from datetime import datetime
from typing import Callable


@dataclass
class SchedulerTask:
    expires_at: datetime
    task: Callable[..., None]
