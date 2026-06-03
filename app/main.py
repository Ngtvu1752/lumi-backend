from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.v1 import auth, devices, energy, habits, sleep, survey, users
from app.cache.energy_cache import get_redis
from app.core.config import settings
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify DB connection
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    # Verify Redis connection
    r = await get_redis()
    await r.ping()
    yield
    # Shutdown: dispose DB engine
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Mount v1 routes
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(sleep.router, prefix=settings.API_V1_PREFIX)
app.include_router(energy.router, prefix=settings.API_V1_PREFIX)
app.include_router(survey.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(habits.router, prefix=settings.API_V1_PREFIX)
app.include_router(devices.router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
