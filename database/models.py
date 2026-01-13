from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    id: int
    user_id: int
    username: Optional[str]
    full_name: str
    created_at: datetime

@dataclass
class Message:
    id: int
    user_id: int
    text: str
    created_at: datetime