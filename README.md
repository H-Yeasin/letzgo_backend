# LetzGo Backend

Backend API for **LetzGo** — a ride-sharing marketplace that connects people heading in the same direction. Passengers can discover nearby ride offers, request to join, and split the fare with the host.

Built with **FastAPI**, **PostgreSQL/PostGIS**, **SQLAlchemy**, **WebSockets**, and **Firebase Cloud Messaging**.

---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Database](#database)
- [API Overview](#api-overview)
- [WebSocket Endpoints](#websocket-endpoints)
- [Core Business Logic](#core-business-logic)
- [Background Jobs](#background-jobs)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Postman Collection](#postman-collection)

---

## Architecture

LetzGo Backend follows a layered service architecture:

```
Client (Mobile / Admin Web)
      │
      ├── HTTP (REST API via FastAPI)
      └── WebSocket (Real-time chat, notifications, match events)
              │
      ┌───────┴────────┐
      │   FastAPI App   │
      │  (app/main.py)  │
      └───────┬────────┘
              │
      ┌───────┴────────┐
      │   API Layer     │  ── Routers / Auth / Rate-limiting
      │  (app/api/v1)   │
      └───────┬────────┘
              │
      ┌───────┴────────┐
      │   Service Layer │  ── Business logic / Validations
      │ (app/services)  │
      └───────┬────────┘
              │
      ┌───────┴────────┐
      │   Data Layer    │  ── SQLAlchemy models / Alembic migrations
      │ (app/models)    │
      └───────┬────────┘
              │
      ┌───────┴────────┐
      │  PostgreSQL +   │  ── Relational data + geospatial queries
      │  PostGIS        │
      └────────────────┘
```

- **REST API** handles CRUD for users, ride pings, matches, ratings, reports, and admin operations.
- **WebSockets** provide real-time messaging, match events (request/accept/decline), and push notifications.
- **Firebase Cloud Messaging (FCM)** delivers push notifications to mobile devices.
- **APScheduler** runs background jobs (ping expiry, chat cleanup, analytics rollups).
- **SlowAPI** applies rate-limiting to protect API endpoints.

---

## Tech Stack

| Layer         | Technology                                                         |
|---------------|--------------------------------------------------------------------|
| Framework     | [FastAPI](https://fastapi.tiangolo.com/) 0.115                     |
| ORM           | [SQLAlchemy](https://www.sqlalchemy.org/) 2.0                      |
| Database      | [PostgreSQL](https://www.postgresql.org/) + [PostGIS](https://postgis.net/) |
| Migrations    | [Alembic](https://alembic.sqlalchemy.org/) 1.14                    |
| Auth          | JWT (`python-jose`), bcrypt (`passlib`), Firebase Admin SDK        |
| Real-time     | WebSockets                                                         |
| Push Notif.   | Firebase Cloud Messaging                                           |
| Geospatial    | `GeoAlchemy2`, `GeoPy`                                             |
| Background    | APScheduler                                                        |
| Rate Limiting | SlowAPI                                                            |
| Validation    | Pydantic v2                                                        |

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ with PostGIS extension
- Redis (optional — for future caching/sessions)
- Firebase Admin SDK credentials (for push notifications)

### Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd letzgo_backend

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate    # Linux/macOS
venv\Scripts\activate       # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create the PostgreSQL database
createdb letzgo_db

# 5. Enable PostGIS extension
psql letzgo_db -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# 6. Configure environment
cp .env.example .env
# Edit .env with your database URL, JWT secret, and Firebase credentials

# 7. Run database migrations
alembic upgrade head

# 8. Start the development server
python scripts/run.py
# or
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The server starts at `http://localhost:8000`. Interactive API docs are available at `/docs` (when `DEBUG=true`).

---

## Configuration

All environment variables are defined in [app/core/config.py](app/core/config.py) via `pydantic-settings`:

| Variable                   | Default                            | Description                       |
|----------------------------|------------------------------------|-----------------------------------|
| `APP_NAME`                 | `LetzGo`                           | Application name                  |
| `APP_VERSION`              | `0.1.0`                            | API version                       |
| `DEBUG`                    | `true`                             | Enable debug mode and API docs    |
| `DATABASE_URL`             | `postgresql://postgres:password@localhost:5432/letzgo_db` | PostgreSQL connection string |
| `JWT_SECRET`               | `your-jwt-secret-key-change-in-production` | Secret used to sign JWT tokens |
| `JWT_ALGORITHM`            | `HS256`                            | JWT signing algorithm             |
| `JWT_EXPIRY_HOURS`         | `72`                               | Token lifetime in hours           |
| `FIREBASE_CREDENTIALS_PATH`| `./firebase-credentials.json`      | Path to Firebase service account  |
| `REDIS_URL`                | `redis://localhost:6379/0`         | Redis connection URL              |
| `ALLOWED_ORIGINS`          | `http://localhost:3000,http://localhost:5173` | CORS allowed origins |

Create a `.env` file in the project root to override any of these defaults.

---

## Database

### Migrations

Alembic is configured in `alembic.ini`. Migration scripts live in `alembic/versions/`.

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply all pending migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1
```

### Models

| Model              | Table                | Description                                     |
|--------------------|----------------------|-------------------------------------------------|
| User               | `profiles`           | User profiles with phone, gender, rating, trust |
| RidePing           | `ride_pings`         | Ride offers with pickup/destination geolocation  |
| MatchRequest       | `match_requests`     | Join requests from passenger to host            |
| Match              | `matches`            | Confirmed ride matches                          |
| ChatMessage        | `chat_messages`      | In-ride chat between host and passenger         |
| Notification       | `notifications`      | In-app notification records                     |
| DeviceToken        | `device_tokens`      | Firebase device tokens for push notifications   |
| Rating             | `ratings`            | Post-ride ratings (1-5 with tags)               |
| Report             | `reports`            | User reports (harassment, no-show, etc.)        |
| FareSplit          | `fare_splits`        | Fare division with host/guest share tracking    |
| BlockedUser        | `blocked_users`      | User-level blocking for safety                  |

### PostGIS

Geographic queries use PostGIS `GEOGRAPHY` types for accurate meter-based distance calculations. Key indexes are defined on `ride_pings.pickup_geom` and `ride_pings.destination_geom` (see `a1b2c3d4e5f6_add_gist_indexes_for_ride_pings.py`).

---

## API Overview

Base URL: `/api/v1`

### Authentication

| Method | Endpoint       | Description          |
|--------|----------------|----------------------|
| POST   | `/auth/signup` | Register with phone  |
| POST   | `/auth/login`  | Login, receive JWT   |
| POST   | `/auth/verify` | Verify OTP / phone   |

All authenticated endpoints require the `Authorization: Bearer <token>` header.

### Users

| Method | Endpoint               | Description                       |
|--------|------------------------|-----------------------------------|
| GET    | `/users/me`            | Get current user profile          |
| PATCH  | `/users/me`            | Update profile                    |
| GET    | `/users/{id}`          | Get another user's profile (limited view) |

### Ride Pings

| Method | Endpoint                   | Description                             |
|--------|----------------------------|----------------------------------------|
| POST   | `/pings`                   | Create a ride offer (host)             |
| GET    | `/pings/nearby`            | Find nearby open rides (passenger)     |
| GET    | `/pings/find`              | Find rides matching a destination      |
| GET    | `/pings/{id}`              | Get ride details                       |
| GET    | `/pings/my`                | List user's own pings                  |
| PATCH  | `/pings/{id}`              | Update a ping (host only)              |
| DELETE | `/pings/{id}`              | Cancel a ping (host only)              |

### Matching

| Method | Endpoint                              | Description                                   |
|--------|---------------------------------------|-----------------------------------------------|
| POST   | `/matches/request`                    | Request to join a ride (passenger)            |
| GET    | `/matches/requests/{ride_id}/pending` | List pending join requests (host only)        |
| POST   | `/matches/accept`                     | Accept a join request (host)                  |
| POST   | `/matches/decline`                    | Decline a join request (host)                 |
| POST   | `/matches/{match_id}/cancel`          | Cancel a match                                |
| POST   | `/matches/{match_id}/start`           | Start a ride (in_progress)                    |
| POST   | `/matches/{match_id}/complete`        | Complete a ride                               |
| GET    | `/matches/active`                     | Get active matches for current user           |
| GET    | `/matches/history`                    | Get ride history                              |

### Fare Splits

| Method | Endpoint                        | Description                            |
|--------|---------------------------------|----------------------------------------|
| POST   | `/fare/calculate`               | Calculate fare split                   |
| POST   | `/fare/{split_id}/pay`          | Mark fare as paid                      |
| POST   | `/fare/{split_id}/confirm`      | Confirm fare payment received          |
| POST   | `/fare/{split_id}/dispute`      | Dispute a fare                         |

### Chat

| Method | Endpoint                        | Description                            |
|--------|---------------------------------|----------------------------------------|
| GET    | `/chat/{match_id}/messages`     | Get message history for a match        |
| POST   | `/chat/{match_id}/send`         | Send a text message                    |

### Ratings

| Method | Endpoint                        | Description                            |
|--------|---------------------------------|----------------------------------------|
| POST   | `/ratings`                      | Submit a rating (1-5)                  |
| GET    | `/ratings/user/{user_id}`       | Get ratings for a user                 |

### Reports

| Method | Endpoint                        | Description                            |
|--------|---------------------------------|----------------------------------------|
| POST   | `/reports`                      | Report a user                          |

### Notifications

| Method | Endpoint                        | Description                            |
|--------|---------------------------------|----------------------------------------|
| GET    | `/notifications`                | List user's notifications              |
| PATCH  | `/notifications/{id}/read`      | Mark notification as read              |
| POST   | `/notifications/device-token`   | Register a Firebase device token       |

### Admin

| Method | Endpoint                                   | Description                      |
|--------|---------------------------------------------|----------------------------------|
| GET    | `/admin/users`                              | List all users                   |
| GET    | `/admin/users/{id}`                         | View user details                |
| POST   | `/admin/users/{id}/block`                   | Block a user                     |
| POST   | `/admin/users/{id}/unblock`                 | Unblock a user                   |
| GET    | `/admin/reports`                            | List all reports                 |
| PATCH  | `/admin/reports/{id}`                       | Update report status             |
| GET    | `/admin/stats`                              | Platform analytics               |

### Geo / Utilities

| Method | Endpoint                        | Description                            |
|--------|---------------------------------|----------------------------------------|
| POST   | `/geocode/reverse`              | Reverse geocode coordinates → label    |

---

## WebSocket Endpoints

### Chat — `/ws/chat/{match_id}`
Real-time messaging between matched riders. Messages are broadcast to all participants in the match.

### Notifications — `/ws/notifications`
Real-time notification stream. Connected clients receive push notifications as they are generated.

### Matches — `/ws/matches`
Real-time match lifecycle events. Clients receive updates when a join request is sent, accepted, declined, or cancelled.

---

## Core Business Logic

### Ride Ping Flow
1. **Host** creates a ride ping (`POST /pings`) specifying pickup location, destination, estimated fare, passenger capacity, and gender preference.
2. **Passengers** discover nearby open rides via `GET /pings/nearby` (uses PostGIS `ST_DWithin` for radius search) or `GET /pings/find` (destination-aware search).
3. **Passengers** request to join (`POST /matches/request`).
4. **Host** reviews pending requests and accepts or declines.
5. On acceptance, a **Match** is created, passengers are incremented, and real-time notifications are sent.

### Gender Preference Rule
Gender preferences are strictly enforced:
- `any` — anyone can join
- `male_only` / `male` — only male-identifying users can join
- `female_only` / `female` — only female-identifying users can join

### Capacity Rule
A ride's available seats = `max_passengers - current_passengers`. Once at capacity, the ride is hidden from the nearby feed and new join requests are rejected.

### Trust Levels
In the nearby feed, host profiles are anonymized to protect privacy. Instead of full profiles, riders see a trust level:
- **High** — 20+ completed rides with 4.5+ rating
- **Medium** — 5+ rides with 4.0+ rating
- **Low** — below thresholds
- **Unknown** — no host data available

### Fare Splits
Fare splits track the division of ride costs between host and passenger. Each split has independent host and guest status (pending → paid/confirmed/disputed), allowing both parties to confirm payment.

### Privacy & Safety
- **Blocked users** are excluded from search results and cannot send join requests.
- **Reports** allow users to report safety concerns (harassment, no-show, fake profile, unsafe behavior, etc.) with admin review workflow.
- **Incomplete profiles** cannot create ride pings or request to join.

---

## Background Jobs

Managed by APScheduler and initialized during app startup:

| Job                    | Interval | Description                              |
|------------------------|----------|------------------------------------------|
| `expire_stale_pings`   | 1 min    | Auto-expire ride pings past their expiry |
| `cleanup_old_chat_messages` | 6 hrs | Remove chat messages older than retention period |
| `cleanup_stale_matches` | 1 hr    | Clean up stale/abandoned match records   |
| `compute_analytics_rollup` | 24 hrs | Aggregate daily platform analytics     |

---

## Testing

Tests are located in the `tests/` directory and use **pytest** with mocked database sessions.

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_core_rules.py -v

# Run with coverage
pytest --cov=app tests/
```

The test suite (`tests/test_core_rules.py`) covers the core marketplace logic:
- Gender join rule enforcement
- Capacity checks (request, accept, cancel lifecycle)
- Nearby feed filtering (capacity, expiry, blocked users)
- Pre-join host profile visibility (anonymized view)
- Join request preconditions (not own ride, not expired, complete profile, no duplicates)

---

## Project Structure

```
letzgo_backend/
├── alembic/                    # Database migrations
│   └── versions/               # Migration scripts
├── app/
│   ├── api/
│   │   └── v1/                 # Route handlers
│   │       ├── auth.py         # Signup / login / verify
│   │       ├── users.py        # User profile CRUD
│   │       ├── pings.py        # Ride ping CRUD + nearby search
│   │       ├── matches.py      # Match request lifecycle
│   │       ├── rides.py        # Ride state transitions
│   │       ├── chat.py         # Chat message endpoints
│   │       ├── ratings.py      # Rating submission & queries
│   │       ├── reports.py      # User reports
│   │       ├── notifications.py # Notification + device tokens
│   │       ├── fare.py         # Fare split management
│   │       ├── geocode.py      # Geocoding utilities
│   │       └── admin.py        # Admin dashboard endpoints
│   ├── core/
│   │   ├── config.py           # Pydantic settings / env config
│   │   ├── constants.py        # Enums and magic constants
│   │   ├── exceptions.py       # Custom exception classes
│   │   ├── permissions.py      # Authorization helpers
│   │   ├── security.py         # JWT, password hashing, auth dependency
│   │   └── websocket_auth.py   # WebSocket auth helpers
│   ├── db/
│   │   ├── base.py             # SQLAlchemy Base + TimestampMixin
│   │   └── session.py          # Database session dependency
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── ride_ping.py
│   │   ├── match_request.py
│   │   ├── match.py
│   │   ├── chat_message.py
│   │   ├── notification.py
│   │   ├── device_token.py
│   │   ├── rating.py
│   │   ├── report.py
│   │   ├── fare_split.py
│   │   └── blocked_user.py
│   ├── schemas/                # Pydantic request/response schemas
│   │   ├── user.py
│   │   ├── ping.py
│   │   ├── match.py
│   │   ├── chat.py
│   │   ├── notification.py
│   │   ├── ride.py
│   │   ├── ride_ping.py
│   │   ├── rating_report.py
│   │   └── admin.py
│   ├── services/               # Business logic layer
│   │   ├── user_service.py
│   │   ├── ping_service.py
│   │   ├── match_service.py
│   │   ├── chat_service.py
│   │   ├── notification_service.py
│   │   ├── rating_service.py
│   │   ├── report_service.py
│   │   ├── ride_state_service.py
│   │   └── websocket_manager.py
│   ├── tasks/                  # Background task functions
│   │   ├── expire_pings.py
│   │   ├── cleanup_chat.py
│   │   ├── cleanup_matches.py
│   │   └── analytics_rollup.py
│   ├── utils/                  # Utility modules
│   │   └── geo.py              # Geospatial helpers (WKT, coordinates)
│   ├── websocket/
│   │   └── handlers/           # WebSocket event handlers
│   │       ├── chat_handler.py
│   │       ├── match_handler.py
│   │       └── notification_handler.py
│   └── main.py                 # FastAPI app entry point
├── scripts/
│   ├── run.py                  # Development server launcher
│   └── create_admin.py         # Admin user creation utility
├── tests/
│   └── test_core_rules.py      # Marketplace rule engine tests
├── uploads/                    # File uploads directory
├── alembic.ini                 # Alembic configuration
├── requirements.txt            # Python dependencies
├── firebase-credentials.json   # Firebase service account (not committed)
└── LetzGo-API.postman_collection.json  # Postman API collection
```

---

## Postman Collection

The file `LetzGo-API.postman_collection.json` includes a complete Postman collection with all API endpoints, example payloads, and environment variables. Import it into Postman to explore the API interactively.

---

## License

Private — internal project.
