from dataclasses import dataclass
from typing import (Optional)


@dataclass
class User:
    """Class representing a Gigantum User Identity"""
    username: Optional[str] = None
    email: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
