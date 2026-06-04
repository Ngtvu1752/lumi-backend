"""Seed the sound catalog with default sleep sounds.

16 tracks across 6 categories, curated for sleep optimization.
File URLs point to a CDN/storage location — update SOUNDS_BASE_URL
to point to your actual audio hosting.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sound import SoundTrack

SOUNNDS_PREFIX = "lumi-sounds"

SOUNDS = [
    {
        "sound_id": "white_noise",
        "name": "White Noise",
        "description": "Classic broadband white noise — masks background sounds and promotes focus or sleep.",
        "category": "white_noise",
        "duration_seconds": 0,  # loop
        "file_url": f"{SOUNNDS_PREFIX}/white_noise.mp3",
        "thumbnail_url": f"{SOUNNDS_PREFIX}/thumbnails/white_noise.png",
        "sort_order": 1,
    },
    {
        "sound_id": "pink_noise",
        "name": "Pink Noise",
        "description": "Softer than white noise with balanced frequencies — studies show deeper sleep.",
        "category": "white_noise",
        "duration_seconds": 0,
        "file_url": f"{SOUNNDS_PREFIX}/pink_noise.mp3",
        "thumbnail_url": f"{SOUNNDS_PREFIX}/thumbnails/pink_noise.png",
        "sort_order": 2,
    },
    {
        "sound_id": "brown_noise",
        "name": "Brown Noise",
        "description": "Deep, low-frequency rumble — excellent for relaxation and masking tinnitus.",
        "category": "white_noise",
        "duration_seconds": 0,
        "file_url": f"{SOUNNDS_PREFIX}/brown_noise.mp3",
        "thumbnail_url": f"{SOUNNDS_PREFIX}/thumbnails/brown_noise.png",
        "sort_order": 3,
    },
    # ── Rain ─────────────────────────────────────────────────
    {
        "sound_id": "rain_light",
        "name": "Light Rain",
        "description": "Gentle drizzle on a window — the most popular natural sleep sound worldwide.",
        "category": "rain",
        "duration_seconds": 0,
        "file_url": f"{SOUNNDS_PREFIX}/rain_light.mp3",
        "thumbnail_url": f"{SOUNNDS_PREFIX}/thumbnails/rain_light.png",
        "sort_order": 10,
    },
    {
        "sound_id": "rain_heavy",
        "name": "Heavy Rain",
        "description": "Intense rainfall with deep bass — powerful mask for noisy environments.",
        "category": "rain",
        "duration_seconds": 0,
        "file_url": f"{SOUNNDS_PREFIX}/rain_heavy.mp3",
        "thumbnail_url": f"{SOUNNDS_PREFIX}/thumbnails/rain_heavy.png",
        "sort_order": 11,
    },
    {
        "sound_id": "thunderstorm",
        "name": "Thunderstorm",
        "description": "Distant thunder with steady rain — creates a cozy, protective atmosphere.",
        "category": "rain",
        "duration_seconds": 0,
        "file_url": f"{SOUNNDS_PREFIX}/thunderstorm.mp3",
        "thumbnail_url": f"{SOUNNDS_PREFIX}/thumbnails/thunderstorm.png",
        "sort_order": 12,
    },
    # ── Ocean ────────────────────────────────────────────────
    {
        "sound_id": "ocean_waves",
        "name": "Ocean Waves",
        "description": "Rhythmic waves crashing on shore — natural rhythm syncs with breathing.",
        "category": "ocean",
        "duration_seconds": 0,
        "file_url": f"{SOUNNDS_PREFIX}/ocean_waves.mp3",
        "thumbnail_url": f"{SOUNNDS_PREFIX}/thumbnails/ocean_waves.png",
        "sort_order": 20,
    },
    {
        "sound_id": "ocean_calm",
        "name": "Calm Ocean",
        "description": "Gentle lapping of calm sea water — minimal variation for deep relaxation.",
        "category": "ocean",
        "duration_seconds": 0,
        "file_url": f"{SOUNNDS_PREFIX}/ocean_calm.mp3",
        "thumbnail_url": f"{SOUNNDS_PREFIX}/thumbnails/ocean_calm.png",
        "sort_order": 21,
    },
    # ── Nature ───────────────────────────────────────────────
    {
        "sound_id": "forest_birds",
        "name": "Forest with Birds",
        "description": "Morning forest ambiance with gentle bird songs — great for waking up.",
        "category": "nature",
        "duration_seconds": 0,
        "file_url": f"{SOUNNDS_PREFIX}/forest_birds.mp3",
        "thumbnail_url": f"{SOUNNDS_PREFIX}/thumbnails/forest_birds.png",
        "sort_order": 30,
    },
    {
        "sound_id": "forest_night",
        "name": "Night Forest",
        "description": "Crickets and gentle wind through trees — peaceful nighttime wilderness.",
        "category": "nature",
        "duration_seconds": 0,
        "file_url": f"{SOUNNDS_PREFIX}/forest_night.mp3",
        "thumbnail_url": f"{SOUNNDS_PREFIX}/thumbnails/forest_night.png",
        "sort_order": 31,
    },
    {
        "sound_id": "wind_gentle",
        "name": "Gentle Wind",
        "description": "Soft breeze through open fields — calming and non-distracting.",
        "category": "nature",
        "duration_seconds": 0,
        "file_url": f"{SOUNNDS_PREFIX}/wind_gentle.mp3",
        "thumbnail_url": f"{SOUNNDS_PREFIX}/thumbnails/wind_gentle.png",
        "sort_order": 32,
    },
    # ── Ambient ──────────────────────────────────────────────
    {
        "sound_id": "campfire",
        "name": "Campfire",
        "description": "Crackling fire with gentle pops — evokes warmth and safety.",
        "category": "ambient",
        "duration_seconds": 0,
        "file_url": f"{SOUNNDS_PREFIX}/campfire.mp3",
        "thumbnail_url": f"{SOUNNDS_PREFIX}/thumbnails/campfire.png",
        "sort_order": 40,
    },
    {
        "sound_id": "fan",
        "name": "Fan Sound",
        "description": "Steady fan hum — familiar and comforting, perfect for masking snoring.",
        "category": "ambient",
        "duration_seconds": 0,
        "file_url": f"{SOUNNDS_PREFIX}/fan.mp3",
        "thumbnail_url": f"{SOUNNDS_PREFIX}/thumbnails/fan.png",
        "sort_order": 41,
    },
    {
        "sound_id": "stream",
        "name": "Babbling Stream",
        "description": "Water flowing over smooth rocks — natural white noise with organic variation.",
        "category": "ambient",
        "duration_seconds": 0,
        "file_url": f"{SOUNNDS_PREFIX}/stream.mp3",
        "thumbnail_url": f"{SOUNNDS_PREFIX}/thumbnails/stream.png",
        "sort_order": 42,
    },
    # ── ASMR ─────────────────────────────────────────────────
    {
        "sound_id": "heartbeat",
        "name": "Heartbeat",
        "description": "Steady resting heartbeat — primal comfort sound, especially for infants and anxiety.",
        "category": "ASMR",
        "duration_seconds": 0,
        "file_url": f"{SOUNNDS_PREFIX}/heartbeat.mp3",
        "thumbnail_url": f"{SOUNNDS_PREFIX}/thumbnails/heartbeat.png",
        "sort_order": 50,
    },
    {
        "sound_id": "asmr_whisper",
        "name": "Soft Whispers",
        "description": "Gentle whispering sounds — triggers ASMR tingles for deep relaxation.",
        "category": "ASMR",
        "duration_seconds": 0,
        "file_url": f"{SOUNNDS_PREFIX}/asmr_whisper.mp3",
        "thumbnail_url": f"{SOUNNDS_PREFIX}/thumbnails/asmr_whisper.png",
        "sort_order": 51,
    },
]


async def seed_sounds(db: AsyncSession) -> int:
    """Insert all default sounds into the database if they don't already exist.

    Returns the number of newly inserted sounds.
    """
    inserted = 0
    for sound_data in SOUNDS:
        existing = await db.get(SoundTrack, sound_data["sound_id"])
        if existing is None:
            db.add(SoundTrack(**sound_data))
            inserted += 1

    if inserted > 0:
        await db.flush()

    return inserted
