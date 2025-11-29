from __future__ import annotations

from typing import List

from models import UserLog


def calculate_calories_for_serving(
    calories_per_serving: float,
    standard_serving_size: float,
    user_serving_size: float,
) -> float:
    """
    Calculate total calories based on user's serving size.

    Formula:
        Total = (Calories_per_serving / Standard_serving_size) * User_serving_size

    All inputs are converted to float and validated.
    Raises:
      - ValueError for non-numeric input
      - ZeroDivisionError if standard_serving_size == 0
    """
    try:
        cal = float(calories_per_serving)
        std_size = float(standard_serving_size)
        user_size = float(user_serving_size)
    except (TypeError, ValueError):
        raise ValueError("All serving and calorie values must be numeric.")

    if std_size == 0:
        # Explicitly guard against division by zero
        raise ZeroDivisionError("Standard serving size cannot be zero.")

    return (cal / std_size) * user_size


def total_daily_calories(logs: List[UserLog]) -> float:
    """
    Sum total calories from a list of user logs.
    """
    return sum(log.calories for log in logs)


def filter_logs_by_meal_type(logs: List[UserLog], meal_type: str) -> List[UserLog]:
    """
    Filter a list of logs by meal type (case-insensitive).
    """
    meal_type_lower = meal_type.lower()
    return [log for log in logs if log.meal_type.lower() == meal_type_lower]