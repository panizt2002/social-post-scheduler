# Social Post Scheduler

An event-driven system for scheduling social media posts. Users schedule posts through a REST API; when a post's time arrives it is sent to Kafka, and a separate Java service consumes it, publishes it and reports the result back.

## Architecture

```
 client ──REST──▶ API (Django + PostgreSQL)
                    │
                    │ scheduler polls for due posts
                    ▼
                 Kafka topic: posts.due
                    │
                    ▼
            Publisher (Java consumer) ──REST──▶ API: PATCH /posts/{id}/status/
```

| Component | Tech | Responsibility |
|---|---|---|
| `api` | Python, Django REST Framework, PostgreSQL | Create, list and cancel posts; store state |
| `scheduler` | Django management command, Kafka producer | Find due posts, send them to Kafka, mark them `queued` |
| `publisher` | Java 17, Kafka consumer | Publish each post (simulated), retry with backoff, report `published` or `failed` |

Post lifecycle: `scheduled → queued → published | failed`, or `scheduled → cancelled`.

Design notes:
- **No lost posts.** A post is marked `queued` only after Kafka confirms delivery; if Kafka is down it stays `scheduled` and is retried on the next poll.
- **No double scheduling.** The scheduler locks rows with `SELECT ... FOR UPDATE SKIP LOCKED`, so several scheduler instances can run safely.
- **At-least-once processing.** The publisher commits Kafka offsets only after a batch is handled, and messages are keyed by post id.
- **Retries.** Publishing and status updates retry with exponential backoff; malformed messages are logged and skipped.

## Run it

Requires Docker.

```bash
docker compose up --build
```

Schedule a post one minute from now:

```bash
curl -X POST http://localhost:8000/api/posts/ \
  -H "Content-Type: application/json" \
  -d "{\"content\": \"Hello from the scheduler\", \"platform\": \"linkedin\", \"scheduled_at\": \"$(date -u -d '+1 minute' +%Y-%m-%dT%H:%M:%SZ)\"}"
```

Watch it move through the pipeline:

```bash
curl http://localhost:8000/api/posts/
docker compose logs -f publisher
```

## API

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/posts/` | Schedule a post (`content`, `platform`, `scheduled_at`) |
| GET | `/api/posts/?status=scheduled` | List posts, optionally by status |
| GET | `/api/posts/{id}/` | Get one post |
| POST | `/api/posts/{id}/cancel/` | Cancel a scheduled post |
| PATCH | `/api/posts/{id}/status/` | Report a publish result (used by the publisher) |

## Tests

```bash
cd api && pip install -r requirements.txt && python manage.py test
cd publisher && mvn test
```

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on every push and pull request:
1. API tests against a real PostgreSQL service container
2. Publisher build and JUnit tests
3. Docker image builds for both services, pushed to GitHub Container Registry on merges to `main`
