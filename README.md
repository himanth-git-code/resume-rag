# AI Professional Identity Platform

Turns a job seeker's resume and notes into a structured candidate knowledge base. The knowledge base powers interview question intelligence, an employer-facing AI chatbot and a generated personal website. The full product spec is in [docs/SPEC.md](docs/SPEC.md).

> Status: project scaffold only. No product features yet.

## Architecture

Modular monolith:

```
Next.js (frontend/) ──/api/* rewrite──▶ Django REST (backend/)
                                          ├─ PostgreSQL + pgvector  (source of truth)
                                          ├─ Redis                  (Celery broker/results)
                                          ├─ Celery worker          (async/AI jobs)
                                          └─ S3 / MinIO             (private documents)
```

- **backend/**: Django 5.2 LTS and DRF.
  - Settings are split into `config/settings/{base,dev,prod,test}.py`, and all config comes from env vars.
  - Domain apps live in `backend/apps/`, and business logic goes in each app's `services.py`.
- **frontend/**: Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui, TanStack Query and Zod.
  - The browser only calls same-origin `/api/*`, which Next.js proxies to Django. There's no CORS setup.
- **docker-compose.yml**: postgres (pgvector), redis, minio (plus a bucket init job), backend, celery and frontend.

## Environment variables

Copy `.env.example` to `.env`. Every variable is documented there.

| Variable | Purpose |
| --- | --- |
| `DJANGO_SETTINGS_MODULE` | `config.settings.dev` locally, `config.settings.prod` in production |
| `DJANGO_SECRET_KEY` | Django secret key (required) |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts |
| `DATABASE_URL` | Postgres connection URL |
| `REDIS_URL` | Redis URL for the Celery broker and result backend |
| `S3_*` | S3-compatible storage (MinIO locally) |

Production only: `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SECURE_HSTS_SECONDS`.

## Local setup

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec backend python manage.py migrate
```

| URL | Service |
| --- | --- |
| http://localhost:3000 | Frontend (shows backend health) |
| http://localhost:8000/api/health/ | Backend health check |
| http://localhost:9001 | MinIO console (credentials from `.env`) |

## Docker commands

```bash
docker compose up -d --build        # start / rebuild
docker compose logs -f backend      # follow logs (backend, celery, frontend, ...)
docker compose exec backend bash    # shell in the backend container
docker compose down                 # stop (add -v to delete DB and MinIO data)
```

After changing Python requirements or `package.json`, rebuild the image with `docker compose up -d --build`.

## Database migrations

```bash
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
```

## Tests

```bash
docker compose exec backend pytest                                    # all backend tests
docker compose exec backend pytest tests/test_health.py::test_health_ok  # single test

cd frontend
pnpm test     # Vitest
pnpm lint     # ESLint
```

## AI provider configuration

TBD. This lands in Phase 2. AI calls will go through the `AIProvider` abstraction in `backend/apps/ai/`.

## Payment provider configuration

TBD. This lands in Phase 5, with Razorpay behind a provider abstraction and webhook-driven entitlements.

## Deployment notes

TBD. The target is AWS: CloudFront, WAF, ALB, RDS PostgreSQL, S3, ElastiCache and CloudWatch. `config.settings.prod` expects TLS to be terminated at the ALB (`X-Forwarded-Proto`), and `requirements/prod.txt` includes gunicorn.
