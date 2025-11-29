from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class FoodItem:
    """
    Represents a single food item and its calorie information.
    This is a logical representation; the GUI/database can choose how to use it.
    """
    name: str
    calories_per_serving: float
    standard_serving_size: float  # e.g., grams or ml
    unit: str = "g"               # default unit is grams


@dataclass
class UserLog:
    """
    Represents a user's logged meal item (a single entry in the log).
    """
    id: Optional[int]  # database primary key, may be None before insert
    date: str          # stored as 'YYYY-MM-DD'
    meal_type: str     # 'Breakfast', 'Lunch', 'Dinner', 'Snacks', etc.
    food_name: str
    calories: float
    serving_size: str
    notes: Optional[str]
    timestamp: datetime = field(default_factory=datetime.now)