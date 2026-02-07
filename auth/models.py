from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass
class User:
    email: str
    name: str
    plan: str           # demo | basic | pro
    role: str           # admin | user
    active: bool
    paid_until: Optional[str]
