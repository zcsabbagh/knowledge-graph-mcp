"""SM-2 spaced repetition algorithm implementation."""

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class SM2Result:
    """Result of SM-2 calculation."""

    ease_factor: float
    interval_days: int
    repetitions: int
    next_review_at: datetime
    suggested_mastery: float | None = None


def calculate_next_review(
    quality: int,
    difficulty: float = 0.5,
    current_ease_factor: float = 2.5,
    current_interval: int = 0,
    current_repetitions: int = 0,
    current_mastery: float = 0.0,
) -> SM2Result:
    """
    Implement SM-2 spaced repetition algorithm with difficulty adjustment.

    Args:
        quality: 0-5 rating of response quality
            - 5: Perfect response
            - 4: Correct after hesitation
            - 3: Correct with serious difficulty
            - 2: Incorrect, but correct answer easy to recall
            - 1: Incorrect, correct answer remembered
            - 0: Complete blackout
        difficulty: Concept difficulty (0-1), affects interval
        current_ease_factor: Current EF (default 2.5)
        current_interval: Current interval in days
        current_repetitions: Consecutive correct recalls
        current_mastery: Current mastery level (0-1)

    Returns:
        SM2Result with updated parameters and next review date.
    """
    if not 0 <= quality <= 5:
        raise ValueError("Quality must be between 0 and 5")

    # Calculate new ease factor using SM-2 formula
    new_ease_factor = current_ease_factor + (
        0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    )
    new_ease_factor = max(1.3, new_ease_factor)  # Minimum EF is 1.3

    if quality >= 3:  # Correct response
        if current_repetitions == 0:
            new_interval = 1
        elif current_repetitions == 1:
            new_interval = 6
        else:
            new_interval = round(current_interval * new_ease_factor)
        new_repetitions = current_repetitions + 1
    else:  # Incorrect response - reset
        new_repetitions = 0
        new_interval = 1
        # Keep ease factor but don't let it increase on failure
        new_ease_factor = min(new_ease_factor, current_ease_factor)

    # Adjust interval based on difficulty (harder concepts = shorter intervals)
    difficulty_factor = 1 - (difficulty * 0.3)  # 0.7 to 1.0
    new_interval = max(1, round(new_interval * difficulty_factor))

    # Calculate next review date
    next_review = datetime.now() + timedelta(days=new_interval)

    # Suggest mastery update based on quality and repetitions
    suggested_mastery = _calculate_suggested_mastery(
        quality, new_repetitions, current_mastery
    )

    return SM2Result(
        ease_factor=round(new_ease_factor, 2),
        interval_days=new_interval,
        repetitions=new_repetitions,
        next_review_at=next_review,
        suggested_mastery=suggested_mastery,
    )


def _calculate_suggested_mastery(
    quality: int,
    repetitions: int,
    current_mastery: float,
) -> float | None:
    """
    Calculate suggested mastery level based on performance.

    Returns None if no change is suggested.
    """
    # Map quality and repetitions to mastery ranges
    if quality >= 4 and repetitions >= 4:
        target = 0.9 + (quality - 4) * 0.05  # 0.9-0.95 for quality 4-5
    elif quality >= 4 and repetitions >= 2:
        target = 0.75 + (quality - 4) * 0.05  # 0.75-0.80
    elif quality >= 3 and repetitions >= 2:
        target = 0.6
    elif quality >= 3:
        target = 0.4
    elif quality >= 2:
        target = 0.25
    else:
        target = max(0.1, current_mastery - 0.1)  # Decrease slightly

    # Only suggest if it's a meaningful change
    if abs(target - current_mastery) >= 0.05:
        return round(target, 2)

    return None


def calculate_overall_mastery(
    mastery_recall: float,
    mastery_application: float,
    mastery_explanation: float,
) -> float:
    """
    Calculate overall mastery from dimensional mastery scores.

    Weights:
    - Recall: 30%
    - Application: 40%
    - Explanation: 30%
    """
    return round(
        0.3 * mastery_recall + 0.4 * mastery_application + 0.3 * mastery_explanation,
        2,
    )
