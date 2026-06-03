from dataclasses import dataclass


@dataclass
class NudgeWithPriority:
    """A nudge event with an adapted priority score for ranking."""
    nudge_type: str
    message: str
    minute: int
    priority: int  # 1-5, 5 = highest priority


# Priority adjustments based on sleep debt level
HIGH_DEBT_BOOST = {"power_nap": 2, "wind_down": 2, "caffeine_cutoff": 2, "meal_timing": 1, "hydration_taper": 1}
HIGH_DEBT_REDUCE = {"deep_work": -1, "morning_exercise": -1, "strategic_caffeine": -1, "evening_exercise": -1}

LOW_DEBT_BOOST = {"deep_work": 1, "morning_exercise": 1, "strategic_caffeine": 1, "social_creative": 1}
LOW_DEBT_REDUCE = {"power_nap": -1}


def adapt_nudge_priorities(
    nudges: list[dict],
    sleep_debt_mins: float,
    snop_hours: float,
) -> list[dict]:
    """Re-rank nudges based on current sleep debt level.

    High sleep debt → prioritize recovery (nap, wind down, caffeine cutoff)
    Low sleep debt → prioritize productivity (deep work, exercise)

    Args:
        nudges: list of dicts with keys: nudge_type, message, minute
        sleep_debt_mins: current cumulative sleep debt in minutes
        snop_hours: user's personalized SNOP in hours

    Returns:
        Same nudges list with 'priority' key added, sorted by priority (desc) then minute (asc)
    """
    snop_mins = snop_hours * 60
    debt_ratio = sleep_debt_mins / snop_mins if snop_mins > 0 else 0.0

    # Determine adjustment tables
    if debt_ratio > 0.5:
        boosts = HIGH_DEBT_BOOST
        reduces = HIGH_DEBT_REDUCE
    elif debt_ratio < 0.2:
        boosts = LOW_DEBT_BOOST
        reduces = LOW_DEBT_REDUCE
    else:
        boosts = {}
        reduces = {}

    result = []
    for nudge in nudges:
        nudge_type = nudge.get("nudge_type", "")
        base_priority = _get_base_priority(nudge_type)
        adjustment = boosts.get(nudge_type, 0) + reduces.get(nudge_type, 0)
        adapted_priority = max(1, min(5, base_priority + adjustment))

        result.append({
            **nudge,
            "priority": adapted_priority,
        })

    # Sort: highest priority first, then earliest minute
    result.sort(key=lambda n: (-n["priority"], n["minute"]))
    return result


def _get_base_priority(nudge_type: str) -> int:
    """Get base priority for a nudge type (1-5)."""
    priorities = {
        "light_exposure": 5,
        "morning_hydration": 4,
        "morning_stretch": 3,
        "deep_work": 5,
        "morning_exercise": 4,
        "strategic_caffeine": 3,
        "caffeine_cutoff": 5,
        "meal_timing": 4,
        "hydration_taper": 3,
        "power_nap": 4,
        "passive_tasks": 3,
        "afternoon_walk": 3,
        "evening_exercise": 3,
        "social_creative": 2,
        "blue_light": 5,
        "wind_down": 5,
    }
    return priorities.get(nudge_type, 3)
