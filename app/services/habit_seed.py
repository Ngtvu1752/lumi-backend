from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.habit import Habit

# The 16 science-based habits with metadata
HABITS = [
    {
        "habit_id": "light_exposure",
        "name": "Morning Light Exposure",
        "description": "Get 10-15 min of bright natural light to clear sleep inertia and reset your circadian clock.",
        "zone_type": "wake",
        "default_priority": 5,
    },
    {
        "habit_id": "morning_hydration",
        "name": "Morning Hydration",
        "description": "Drink a full glass of water — your body is dehydrated after 7-8h of sleep.",
        "zone_type": "wake",
        "default_priority": 4,
    },
    {
        "habit_id": "morning_stretch",
        "name": "Morning Stretch",
        "description": "Do 5 min of light stretching to activate your body and improve circulation.",
        "zone_type": "wake",
        "default_priority": 3,
    },
    {
        "habit_id": "deep_work",
        "name": "Deep Work Block",
        "description": "Schedule your most important cognitive tasks during peak alertness.",
        "zone_type": "morning_peak",
        "default_priority": 5,
    },
    {
        "habit_id": "morning_exercise",
        "name": "Morning Exercise",
        "description": "Physical activity now boosts alertness and mood for hours.",
        "zone_type": "morning_peak",
        "default_priority": 4,
    },
    {
        "habit_id": "strategic_caffeine",
        "name": "Strategic Caffeine",
        "description": "Pair caffeine with your natural cortisol peak for maximum effect.",
        "zone_type": "morning_peak",
        "default_priority": 3,
    },
    {
        "habit_id": "caffeine_cutoff",
        "name": "Caffeine Cutoff",
        "description": "Stop all caffeine now to protect tonight's sleep quality (half-life 5-6h).",
        "zone_type": "melatonin_window",
        "default_priority": 5,
    },
    {
        "habit_id": "meal_timing",
        "name": "Meal Timing",
        "description": "Finish heavy meals now — digestion too close to bed disrupts sleep.",
        "zone_type": "melatonin_window",
        "default_priority": 4,
    },
    {
        "habit_id": "hydration_taper",
        "name": "Hydration Taper",
        "description": "Start tapering fluid intake to avoid nighttime bathroom trips.",
        "zone_type": "melatonin_window",
        "default_priority": 3,
    },
    {
        "habit_id": "power_nap",
        "name": "Power Nap",
        "description": "A 20-min nap during the afternoon dip reduces sleep debt without grogginess.",
        "zone_type": "afternoon_dip",
        "default_priority": 4,
    },
    {
        "habit_id": "passive_tasks",
        "name": "Passive Task Switch",
        "description": "Switch to routine tasks, emails, or light meetings during low energy.",
        "zone_type": "afternoon_dip",
        "default_priority": 3,
    },
    {
        "habit_id": "afternoon_walk",
        "name": "Afternoon Walk",
        "description": "A short walk outside can boost alertness during the afternoon dip.",
        "zone_type": "afternoon_dip",
        "default_priority": 3,
    },
    {
        "habit_id": "evening_exercise",
        "name": "Evening Exercise Window",
        "description": "Last window for moderate exercise — intense activity later will delay sleep.",
        "zone_type": "evening_peak",
        "default_priority": 3,
    },
    {
        "habit_id": "social_creative",
        "name": "Social & Creative Time",
        "description": "Good window for social activities, creative work, or planning tomorrow.",
        "zone_type": "evening_peak",
        "default_priority": 2,
    },
    {
        "habit_id": "blue_light",
        "name": "Blue Light Reduction",
        "description": "Enable night mode, dim screens to protect melatonin production.",
        "zone_type": "melatonin_window",
        "default_priority": 5,
    },
    {
        "habit_id": "wind_down",
        "name": "Wind Down Routine",
        "description": "Begin your wind down: light reading, breathing exercises, no screens.",
        "zone_type": "melatonin_window",
        "default_priority": 5,
    },
]


async def seed_habits(db: AsyncSession) -> int:
    """Insert all 16 habits into the database if they don't already exist.

    Returns the number of newly inserted habits.
    """
    inserted = 0
    for habit_data in HABITS:
        existing = await db.get(Habit, habit_data["habit_id"])
        if existing is None:
            db.add(Habit(**habit_data))
            inserted += 1

    if inserted > 0:
        await db.flush()

    return inserted
