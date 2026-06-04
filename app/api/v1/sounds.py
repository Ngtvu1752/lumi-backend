import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.sound import SoundPlaybackLog, SoundTrack, UserSoundFavorite
from app.schemas.sound import (
    FavoriteResponse,
    PlaybackLogCreate,
    PlaybackLogResponse,
    PlaybackStatsResponse,
    SoundCategoryResponse,
    SoundTrackResponse,
)
from app.services.sound_seed import seed_sounds
from app.services.s3_storage import generate_presigned_url

router = APIRouter(prefix="/sounds", tags=["sounds"])


# ── Sound Catalog ────────────────────────────────────────────

@router.get("", response_model=list[SoundTrackResponse])
async def list_sounds(
    category: str | None = Query(None, description="Filter by category"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all active sounds, optionally filtered by category.

    Returns sounds with is_favorite flag based on user's favorites.
    """
    stmt = select(SoundTrack).where(SoundTrack.is_active == True)
    if category:
        stmt = stmt.where(SoundTrack.category == category)
    stmt = stmt.order_by(SoundTrack.sort_order)

    result = await db.execute(stmt)
    sounds = result.scalars().all()

    # Get user's favorites
    fav_stmt = select(UserSoundFavorite.sound_id).where(UserSoundFavorite.user_id == user_id)
    fav_result = await db.execute(fav_stmt)
    favorite_ids = {row[0] for row in fav_result.all()}

    return [
        SoundTrackResponse(
            sound_id=s.sound_id,
            name=s.name,
            description=s.description,
            category=s.category,
            duration_seconds=s.duration_seconds,
            file_url=generate_presigned_url(s.file_url),
            thumbnail_url=generate_presigned_url(s.thumbnail_url),
            is_favorite=s.sound_id in favorite_ids,
        )
        for s in sounds
    ]


@router.get("/categories", response_model=list[SoundCategoryResponse])
async def list_categories(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all sound categories with their sounds grouped."""
    stmt = select(SoundTrack).where(SoundTrack.is_active == True).order_by(SoundTrack.sort_order)
    result = await db.execute(stmt)
    sounds = result.scalars().all()

    # Get user's favorites
    fav_stmt = select(UserSoundFavorite.sound_id).where(UserSoundFavorite.user_id == user_id)
    fav_result = await db.execute(fav_stmt)
    favorite_ids = {row[0] for row in fav_result.all()}

    # Group by category
    categories: dict[str, list] = defaultdict(list)
    for s in sounds:
        categories[s.category].append(
            SoundTrackResponse(
                sound_id=s.sound_id,
                name=s.name,
                description=s.description,
                category=s.category,
                duration_seconds=s.duration_seconds,
                file_url=generate_presigned_url(s.file_url),
                thumbnail_url=generate_presigned_url(s.thumbnail_url),
                is_favorite=s.sound_id in favorite_ids,
            )
        )

    return [
        SoundCategoryResponse(category=cat, count=len(tracks), sounds=tracks)
        for cat, tracks in categories.items()
    ]


# ── Favorites ────────────────────────────────────────────────

@router.get("/favorites", response_model=list[SoundTrackResponse])
async def list_favorites(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List user's favorite sounds."""
    stmt = (
        select(SoundTrack)
        .join(UserSoundFavorite, SoundTrack.sound_id == UserSoundFavorite.sound_id)
        .where(UserSoundFavorite.user_id == user_id)
        .where(SoundTrack.is_active == True)
        .order_by(UserSoundFavorite.created_at.desc())
    )
    result = await db.execute(stmt)
    sounds = result.scalars().all()

    return [
        SoundTrackResponse(
            sound_id=s.sound_id,
            name=s.name,
            description=s.description,
            category=s.category,
            duration_seconds=s.duration_seconds,
            file_url=generate_presigned_url(s.file_url),
            thumbnail_url=generate_presigned_url(s.thumbnail_url),
            is_favorite=True,
        )
        for s in sounds
    ]


@router.post("/favorites/{sound_id}", response_model=FavoriteResponse)
async def add_favorite(
    sound_id: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Add a sound to user's favorites."""
    sound = await db.get(SoundTrack, sound_id)
    if not sound or not sound.is_active:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"Sound '{sound_id}' not found")

    existing = await db.get(UserSoundFavorite, (user_id, sound_id))
    if existing:
        return existing  # Already favorited

    fav = UserSoundFavorite(user_id=user_id, sound_id=sound_id)
    db.add(fav)
    await db.flush()
    return fav


@router.delete("/favorites/{sound_id}")
async def remove_favorite(
    sound_id: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Remove a sound from user's favorites."""
    fav = await db.get(UserSoundFavorite, (user_id, sound_id))
    if not fav:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Favorite not found")

    await db.delete(fav)
    await db.flush()
    return {"status": "removed", "sound_id": sound_id}


# ── Playback Logging ─────────────────────────────────────────

@router.post("/playback/log", response_model=PlaybackLogResponse)
async def log_playback(
    payload: PlaybackLogCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Log a sound playback session.

    Called by mobile app when user stops or switches sounds.
    """
    log = SoundPlaybackLog(
        user_id=user_id,
        sound_id=payload.sound_id,
        started_at=payload.started_at,
        duration_seconds=payload.duration_seconds,
    )
    db.add(log)
    await db.flush()
    return log


@router.get("/playback/history", response_model=list[PlaybackLogResponse])
async def get_playback_history(
    days: int = Query(30, ge=1, le=365),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get user's playback history."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(SoundPlaybackLog)
        .where(SoundPlaybackLog.user_id == user_id)
        .where(SoundPlaybackLog.created_at >= cutoff)
        .order_by(SoundPlaybackLog.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/playback/stats", response_model=PlaybackStatsResponse)
async def get_playback_stats(
    days: int = Query(30, ge=1, le=365),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated playback statistics for the user."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Total listening time and sessions
    stats_stmt = select(
        func.coalesce(func.sum(SoundPlaybackLog.duration_seconds), 0).label("total_seconds"),
        func.count(SoundPlaybackLog.log_id).label("total_sessions"),
    ).where(
        SoundPlaybackLog.user_id == user_id,
        SoundPlaybackLog.created_at >= cutoff,
    )
    stats_result = await db.execute(stats_stmt)
    row = stats_result.one()

    total_seconds = int(row.total_seconds or 0)
    total_sessions = int(row.total_sessions or 0)

    # Most played sound
    most_played_stmt = (
        select(SoundPlaybackLog.sound_id)
        .where(SoundPlaybackLog.user_id == user_id, SoundPlaybackLog.created_at >= cutoff)
        .group_by(SoundPlaybackLog.sound_id)
        .order_by(func.count().desc())
        .limit(1)
    )
    most_played_result = await db.execute(most_played_stmt)
    most_played_row = most_played_result.first()
    most_played = most_played_row[0] if most_played_row else None

    # Favorite category (by total listening time)
    fav_cat_stmt = (
        select(SoundTrack.category, func.sum(SoundPlaybackLog.duration_seconds))
        .join(SoundPlaybackLog, SoundTrack.sound_id == SoundPlaybackLog.sound_id)
        .where(SoundPlaybackLog.user_id == user_id, SoundPlaybackLog.created_at >= cutoff)
        .group_by(SoundTrack.category)
        .order_by(func.sum(SoundPlaybackLog.duration_seconds).desc())
        .limit(1)
    )
    fav_cat_result = await db.execute(fav_cat_stmt)
    fav_cat_row = fav_cat_result.first()
    fav_category = fav_cat_row[0] if fav_cat_row else None

    return PlaybackStatsResponse(
        total_listening_minutes=total_seconds // 60,
        total_sessions=total_sessions,
        most_played_sound=most_played,
        favorite_category=fav_category,
    )


# ── Admin ────────────────────────────────────────────────────

@router.post("/seed", response_model=dict)
async def seed_sounds_endpoint(
    db: AsyncSession = Depends(get_db),
):
    """Seed the sound catalog with default tracks (admin utility)."""
    count = await seed_sounds(db)
    return {"seeded": count}


# ── Single Sound (MUST be last — catch-all path param) ──────

@router.get("/{sound_id}", response_model=SoundTrackResponse)
async def get_sound(
    sound_id: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a single sound by ID."""
    sound = await db.get(SoundTrack, sound_id)
    if not sound or not sound.is_active:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"Sound '{sound_id}' not found")

    # Check if favorited
    fav = await db.get(UserSoundFavorite, (user_id, sound_id))

    return SoundTrackResponse(
        sound_id=sound.sound_id,
        name=sound.name,
        description=sound.description,
        category=sound.category,
        duration_seconds=sound.duration_seconds,
        file_url=sound.file_url,
        thumbnail_url=sound.thumbnail_url,
        is_favorite=fav is not None,
    )
