# CQRS Pattern with Sample Todo App (FastAPI, Postgres, Redis, Celery)

A production-ready example of the CQRS pattern implemented or a Todo application using:

- FastAPI for the HTTP API (async)
- PostgreSQL with separate write and read databases
- SQLAlchemy 2.0 async engines with connection pooling
- Redis for both Celery broker and application cache
- Celery workers to replicate write-side changes into the read-side and keep cache coherent

This project demonstrates write/read separation, eventual consistency, cache invalidation strategies, and background replication without impacting API latency.

## Architecture

Flow overview:
- Writes (create/update/delete) go to the write DB; a Celery task replicates the change into the read DB and updates cache.
- Reads hit Redis first; on cache misses due to TTL, data is refilled from the read DB.

![System Architecture](Architecture.png)
Mermaid Code for Architecture
```
flowchart LR

  %% === Client Layer ===
  subgraph Client
    A[Client]
  end

  %% === API Layer ===
  subgraph API_Layer
    B[FastAPI API]
  end

  %% === Data Stores ===
  subgraph Data_Stores
    C[(Postgres Write DB)]
    E[(Postgres Read DB)]
  end

  %% === Redis Services ===
  subgraph Redis_Services
    R[Redis Cache]
    Q["Redis (Celery Broker)"]
  end

  %% === Background Workers ===
  subgraph Background_Workers
    W[Celery Worker]
  end

  %% === Flow ===
  A -->|HTTP Request| B
  B -->|Write Operations| C
  B -->|Read Operations| R
  R -->|Cache Miss / Partial| E
  B -.->|Enqueue Task| Q
  Q -->|Push to Queue| W
  W -->|Replicate to Read DB| E
  W -->|Update Cache| R
```

## Features
- Separate write/read Postgres instances
- Async DB operations with pooling (pre-ping, pool timeout, overflow)
- Redis caching with per-item keys and an index set to avoid TTL-induced partial results
- Celery background workers for read-side replication and cache coherence
- Full CRUD API with clear error handling
- Docker Compose for one-command local setup

## Tech Stack
- Python 3.10, FastAPI, SQLAlchemy 2.0 (async)
- PostgreSQL 15 (write and read instances)
- Redis 7 (broker + cache)
- Celery 5
- Uvicorn

## Project Structure

The project follows a clean, simplified architecture with clear separation of concerns:

```
app/
├── main.py                 # Main FastAPI application entry point
├── celery_app.py          # Celery configuration
├── tasks.py               # Background tasks
├── cache/                 # Cache layer (Redis)
│   └── redis_cache.py
├── config/                # Configuration management
│   └── settings.py
├── db/                    # Database layer
│   ├── models.py
│   ├── schemas.py
│   ├── write_db.py        # async engine + pool (writes)
│   ├── read_db.py         # async engine + pool (reads)
│   └── read_db_sync.py    # sync engine for Celery worker
├── middleware/            # HTTP middleware
│   └── logging_middleware.py
├── routes/                # API routing
│   ├── task_routes.py     # All task endpoints
│   └── index.py           # Route collection
└── services/              # Business logic layer
    └── task_service.py    # All CRUD operations consolidated
```

## Architecture Benefits

### 1. **Simplified Structure**
- **Routes**: Handle HTTP requests and responses
- **Services**: Contain all business logic and CRUD operations
- **Database**: Data access layer with separate read/write DBs
- **Config**: Centralized configuration management

### 2. **Consolidated CRUD Operations**
- All task operations (create, read, update, delete) are centralized in `TaskService`
- No complex separation between commands and queries
- Cleaner, more maintainable code

### 3. **Service Layer**
- Business logic is centralized in the service layer
- Easier to test and maintain
- Reusable across different parts of the application

### 4. **Middleware Support**
- Logging middleware for request/response logging
- Easy to add authentication, CORS, etc.

### 5. **Configuration Management**
- Centralized settings using Pydantic
- Environment variable support
- Easy to manage different environments (dev, staging, prod)

## Data Flow Details

- Create/Update/Delete
  1. API writes to the write DB (async SQLAlchemy).
  2. API enqueues a Celery task.
  3. Worker upserts/deletes in the read DB (sync engine) and updates Redis cache.

- Read
  1. API fetches all task IDs from `tasks:index`.
  2. Performs bulk gets for `task:{id}` keys.
  3. For missing items (TTL expiration), fetches from read DB, repopulates cache, and returns a complete list.
  4. If an indexed ID no longer exists in DB, removes it from the index to prevent future stale reads.

## Cache Strategy (TTL-safe)

- Item key: `task:{id}` with TTL `CACHE_TTL_SECONDS` (default 60s)
- Index key: `tasks:index` (Redis Set of IDs, no TTL)
- On writes: upsert item and ensure ID is in the index
- On deletes: remove item key and remove ID from index
- On reads: use index + refill logic to avoid returning partial lists when some keys expire

## Getting Started

Prerequisites:
- Docker + Docker Compose

Environment variables (defaults work with Compose):

- `WRITE_DB_URL` = `postgresql+asyncpg://postgres:postgres@write_db:5432/write_db`
- `READ_DB_URL` = `postgresql+asyncpg://postgres:postgres@read_db:5432/read_db`
- `READ_DB_SYNC_URL` = same as `READ_DB_URL` but with `+psycopg2` (derived automatically)
- `REDIS_URL` = `redis://redis:6379/0`
- `CACHE_TTL_SECONDS` = `60`

Run locally:

```bash
docker compose up --build -d
```

Services:
- API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- Flower (Celery UI): `http://localhost:5555`
- Postgres (host ports): write on `5433`, read on `5434`

The `init-db` service will create tables on both DBs at startup.

## API

- Create task

```http
POST v1/tasks
Content-Type: application/json

{
  "title": "My Task",
  "description": "Optional description"
}
```

- List tasks

```http
GET v1/tasks
```

- Get task by id

```http
GET v1/tasks/{task_id}
```

- Update task

```http
PUT v1/tasks/{task_id}
Content-Type: application/json

{
  "title": "Updated title",
  "description": "Updated description",
  "is_completed": true
}
```

- Delete task

```http
DELETE v1/tasks/{task_id}
```

You can also use `rest.http` for quick local testing.

## Development

### Adding New Routes
1. Create a new route file in `/app/routes/`
2. Add the router to `/app/routes/index.py`
3. The route will automatically be included in the main application

### Adding New Services
1. Create a new service file in `/app/services/`
2. Implement the business logic and CRUD operations
3. Use the service in your routes

### Adding New Middleware
1. Create a new middleware file in `/app/middleware/`
2. Add it to the main application in `main.py`

### Configuration
- Update `/app/config/settings.py` for new configuration options
- Use environment variables for sensitive data
- The `.env` file is automatically loaded

## Troubleshooting

- API returns fewer tasks than expected
  - The cache uses TTL per item; if items expire, the list endpoint refills them from the read DB. If read DB is empty, ensure the worker is running and Celery tasks are being processed (check Flower).

- Worker cannot connect to DB or Redis
  - Ensure `write_db`, `read_db`, and `redis` services are healthy. The worker depends_on healthchecks and will restart automatically.

- Tables missing
  - `init-db` runs `init_db.py` to create tables in both DBs. Re-run `docker compose up --build` if needed.

## Notes

- Write/read databases are separate for clarity; in production, these might be different clusters or replicas.
- The read path is fully async to maximize throughput; Celery uses a sync engine to avoid async complexity in workers.
- Connection pooling is enabled on all engines with health checks (`pool_pre_ping`).
- The project structure has been simplified from a complex CQRS implementation to a clean, maintainable architecture while preserving all functionality.

## License

MIT

