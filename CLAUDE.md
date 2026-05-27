# LUMI Backend — Comprehensive Bio-Energy Optimization System

## Project Overview

LUMI is a HealthTech backend for a sleep optimization Android app. It goes beyond traditional sleep tracking by acting as a "Comprehensive Bio-Energy Optimization System" — predicting energy levels throughout the day using two core scientific models:

- **Sleep Debt**: cumulative 14-day sliding window of sleep deficit (SNOP minus actual sleep)
- **Borbély Two-Process Model**: interaction between homeostatic sleep pressure (Process S, adenosine buildup) and circadian rhythm (Process C, 5-harmonic sinusoidal equation)

The mobile app (Android/Kotlin/Jetpack Compose, not in this repo) collects data via Health Connect API. This repo contains the Python backend that runs all computation.

## Tech Stack

- **Language**: Python
- **Framework**: FastAPI (async/await)
- **Task Queue**: Celery + Redis (background computation: energy recalculation, SNOP calibration)
- **Database**: PostgreSQL + TimescaleDB (time-series hypertables for sleep sessions and biometric data)
- **Caching**: Redis (energy schedule JSON cached per user, 24h TTL)
- **Math/Science**: NumPy (vectorized time-series), SciPy (differential equations, interpolation)
- **ORM**: SQLAlchemy
- **Containerization**: Docker

## Project Structure

```
LUMI_Backend/
├── app/                  # Main application package (currently empty — greenfield)
├── docs/                 # Project documentation (Vietnamese)
│   ├── business-requirement.md
│   ├── research.md
│   ├── software-requirement-specification.md
│   └── system-design.md
├── Dockerfile            # (empty)
├── requirements.txt      # (empty)
└── CLAUDE.md             # This file
```

## Key Domain Concepts

| Concept | Description |
|---------|-------------|
| SNOP | Sleep Need for Optimal Performance — personalized, calibrated via onboarding survey + Health Connect data |
| Sleep Debt | Sum of (SNOP - actual_sleep) over 14-day sliding window. Warning threshold: 5 hours |
| Process S | Homeostatic sleep pressure (adenosine). τ_r ≈ 18.2h (awake), τ_d ≈ 4.2h (asleep) |
| Process C | Circadian pacemaker, 5-harmonic sinusoidal. Amplitudes: 0.97, 0.22, 0.07, 0.03, 0.001 |
| Energy Schedule | 24h graph from Φ(t) = H(t) - A_c·x(t), A_c = 0.1333. Identifies Wake Zone, Morning/Evening Peaks, Afternoon Dip, Melatonin Window |
| Nudges | Science-based micro-interventions scheduled against the user's circadian phases |

## Database Schema (TimescaleDB)

**Metadata tables (standard PostgreSQL):**
- `users` — user_id (UUID PK), chronotype, snop_hours, current_sleep_debt, created_at
- `user_survey_responses` — user_id (FK), question_id, answer_key

**Hypertables (time-series):**
- `sleep_sessions` — partitioned on `start_time`. Columns: session_id, user_id, start_time, end_time, duration_mins, session_type (nightly/nap)
- `biometric_data` — partitioned on `time` (1-day chunks). Columns: user_id, time, metric_type, value. Compression enabled after 7 days.

## API Architecture

- FastAPI receives HTTPS requests, validates JWT, writes records to TimescaleDB
- Heavy computation (energy recalculation, SNOP calibration) dispatched to Celery workers
- Energy schedule results serialized to Redis cache, served to mobile client at <200ms p95 latency
- Target throughput: 10,000 TPS

## Algorithm Pipeline (Celery Workers)

1. **Sleep Debt Aggregation** — query sleep_sessions, sum SNOP - actual over 14 days
2. **Process S Modeler** — solve ODE: H(t) = 1 - (1-H(t0))·e^(-(t-t0)/18.2)
3. **Process C Modeler** — 5-harmonic sinusoidal via numpy vectorized ops (1,440 data points/day/user)
4. **Synthesis & Nudge Scheduling** — Φ(t) = H(t) - A_c·x(t), find extrema, classify energy zones, generate alert schedule

## Functional Requirements (FR-01 to FR-06)

- FR-01: Onboarding survey (9 questions) → Seed Data for SNOP
- FR-02: Health Connect API sync (SleepSessionRecord, HeartRateRecord) with graceful degradation to manual input
- FR-03: Sleep Debt Dashboard (14-day sliding window, includes naps)
- FR-04: Energy Schedule spline chart (24h, color-coded zones, infinite horizontal scroll)
- FR-05: Adaptive Nudges — notifications shift with circadian rhythm
- FR-06: Google Calendar/Outlook integration — schedule high-focus tasks during Peak zones

## Non-Functional Requirements

- **Security**: TLS 1.3 in transit, AES-256 at rest, HIPAA/GDPR-aligned, anonymized data for analytics
- **Performance**: API p95 < 200ms, async computation via Celery
- **Scalability**: horizontal scaling, INSERT-heavy morning sync burst, TimescaleDB hypertables with columnar compression

## Business Model

- B2C: Freemium → 7-day trial → monthly/annual subscription
- B2B: Enterprise dashboard for HR (anonymized aggregate sleep debt metrics)

## Development Notes

- All documentation is in Vietnamese; domain terms are in English
- Mobile client (Android/Kotlin/Compose) is a separate repo — this repo is backend only
- Seed Data from onboarding survey bootstraps the algorithm before enough Health Connect data accumulates
- Dynamic calibration replaces Seed Data as real data flows in (EMA smoothing)
