"""Run once at startup to create tables and convert to TimescaleDB hypertables."""

import asyncio
import sys

from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine, Base
from app.db.base import (
    User, SleepSession, BiometricData, UserSurveyResponse,
    Habit, UserHabitPreference, HabitLog, DeviceToken,
    SoundTrack, UserSoundFavorite, SoundPlaybackLog,
)


async def init():
    # Create all tables from ORM models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Convert time-series tables to hypertables
    async with engine.begin() as conn:
        # sleep_sessions hypertable (partition by start_time)
        await conn.execute(text("""
            SELECT create_hypertable('sleep_sessions', 'start_time',
                if_not_exists => TRUE);
        """))

        # biometric_data hypertable (partition by time, 1-day chunks)
        await conn.execute(text("""
            SELECT create_hypertable('biometric_data', 'time',
                chunk_time_interval => INTERVAL '1 day',
                if_not_exists => TRUE);
        """))

        # Enable columnar compression on biometric_data
        await conn.execute(text("""
            ALTER TABLE biometric_data SET (
                timescaledb.compress,
                timescaledb.compress_segmentby = 'user_id, metric_type',
                timescaledb.compress_orderby = 'time DESC'
            );
        """))

        # Auto-compress chunks older than 7 days
        await conn.execute(text("""
            SELECT add_compression_policy('biometric_data', INTERVAL '7 days',
                if_not_exists => TRUE);
        """))

    print("[init] Tables and hypertables created successfully.")


if __name__ == "__main__":
    asyncio.run(init())
