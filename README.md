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
                                          └─ S3 / SeaweedFS         (private documents)
```

- **backend/**: Django 5.2 LTS and DRF.
  - Settings are split into `config/settings/{base,dev,prod,test}.py`, and all config comes from env vars.
  - Domain apps live in `backend/apps/`, and business logic goes in each app's `services.py`.
- **frontend/**: Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui, TanStack Query and Zod.
  - The browser only calls same-origin `/api/*`, which Next.js proxies to Django. There's no CORS setup.
- **docker-compose.yml**: postgres (pgvector), redis, seaweedfs (local S3, plus a one-shot `s3-init` bucket job), backend, celery and frontend.

## Environment variables

Copy `.env.example` to `.env`. Every variable is documented there.

| Variable | Purpose |
| --- | --- |
| `DJANGO_SETTINGS_MODULE` | `config.settings.dev` locally, `config.settings.prod` in production |
| `DJANGO_SECRET_KEY` | Django secret key (required) |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts |
| `DATABASE_URL` | Postgres connection URL |
| `REDIS_URL` | Redis URL for the Celery broker and result backend |
| `S3_*` | S3-compatible storage (SeaweedFS locally) |
| `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` | Optional Google sign-in (see below) |

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

Those are the default host ports. If they clash with something else on your machine, set `FRONTEND_PORT` / `BACKEND_PORT` in `.env`. Postgres, Redis and SeaweedFS don't publish host ports; reach them through the containers:

```bash
docker compose exec postgres psql -U ai_identity ai_identity
docker compose exec redis redis-cli
docker compose run --rm --entrypoint aws s3-init --endpoint-url http://seaweedfs:8333 s3 ls   # aws-cli against local S3
```

## Authentication

Sign-up and login use [django-allauth](https://docs.allauth.org/) in headless mode. It's a JSON API under `/_allauth/browser/v1/`, uses Django session cookies and CSRF, and Next.js proxies it so everything stays same-origin.

To enable **Google sign-in**:

1. In Google Cloud Console, go to APIs & Services → Credentials → Create OAuth client ID (type: Web application).
2. Add the authorised redirect URI `http://localhost:3000/accounts/google/login/callback/`.
3. Put the client ID and secret in `.env`, then restart with `docker compose up -d`.

A verified Google email signs into the existing account with that email, if there is one.

## Docker commands

```bash
docker compose up -d --build        # start / rebuild
docker compose logs -f backend      # follow logs (backend, celery, frontend, ...)
docker compose exec backend bash    # shell in the backend container
docker compose down                 # stop (add -v to delete DB and S3 data)
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

## Resume upload and parsing

1. `POST /api/resumes/` validates the file by its content, not its name: PDF or DOCX, at most `RESUME_MAX_UPLOAD_MB` MB and `RESUME_MAX_PDF_PAGES` pages. It extracts the text and stores the file in private S3 under an opaque key.
   - PDFs without a text layer (scanned images) are rejected straight away, because there's no OCR yet.
2. A Celery task (`apps.resume_parser.tasks.process_resume`) sends the text to the AI provider and stores a structured draft on the `ResumeParseJob`.
   - Transient AI errors are retried with backoff. Permanent errors fail the job with a message that's safe to show the candidate.
3. The frontend polls the job until it's `ready_for_review` or `failed`. The draft is never written to the profile until the candidate reviews and saves it.

## Candidate profile (review and save)

- `GET /api/resumes/jobs/<id>/draft/` returns a job's AI draft, shaped like a profile. Missing data is `null`.
- `GET /api/profile/` returns the saved profile.
- `PUT /api/profile/` (optionally with `job_id`) replaces the whole profile in one transaction. It's the only code path that writes profile data, and saving with a `job_id` marks that job `applied`.
  - Each saved row records `source_type` (`resume` or `candidate_input`), and resume-sourced rows link to the source document for later grounding.
- Links must be `http(s)` or have no scheme. `javascript:`, `data:` and similar are rejected, because these links will later be shown to employers.

**Malware scanning (planned):** uploads are only ever parsed as PDF/DOCX, never executed or served back publicly. Before files are shared or served to anyone else, a ClamAV scan step will run between upload and extraction.

## Knowledge base

`apps.knowledge_base` indexes each candidate's **approved** profile and notes for semantic search. The raw resume text is never indexed, because it may contain things the candidate removed during review.

- **Chunks:** one per role, project, education, certification and achievement; one for the basics; one per skill category; and notes split on paragraphs at about 1,500 characters. Each has a stable key (`experience:12`, `note:5:0`) and a `source_type` / `source_id` pointing back to the profile row.
- **Rebuilds** run in Celery after every profile or note change. They're incremental: only new or changed chunks are embedded, and removed data is deleted. A per-user lock serialises concurrent rebuilds. If embedding fails, the existing knowledge base stays as it was.
- **Retrieval:** `CandidateRetrievalService.search(user, query)` runs cosine search on pgvector (HNSW index), always filtered to that one candidate. It's used by the Phase 3 employer chatbot.
- Profile items keep their IDs across saves, so anything citing `source_id` stays valid.

Embeddings use `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL` / `VOYAGE_API_KEY` (Voyage `voyage-4`, 1024 dimensions). `fake` works without a key, but its search results aren't meaningful.

## AI provider configuration

All AI calls go through `apps.ai.providers.get_provider()` (the `AIProvider` interface in `backend/apps/ai/`), so business logic never imports a vendor SDK.

| Variable | Purpose |
| --- | --- |
| `AI_PROVIDER` | `anthropic` for real parsing; `fake` makes no API calls and returns an empty draft |
| `AI_MODEL` | Model ID, default `claude-opus-5` |
| `ANTHROPIC_API_KEY` | Required when `AI_PROVIDER=anthropic` |
| `EMBEDDING_PROVIDER` | `voyage` for real embeddings; `fake` needs no key |
| `EMBEDDING_MODEL` | Voyage model, default `voyage-4` (1024 dimensions) |
| `VOYAGE_API_KEY` | Required when `EMBEDDING_PROVIDER=voyage` |

The Anthropic provider uses structured outputs (a Pydantic schema) with adaptive thinking. It also enables the API's server-side refusal fallback. Resume text is never logged; only job IDs, token counts and error types are.

## Payment provider configuration

TBD. This lands in Phase 5, with Razorpay behind a provider abstraction and webhook-driven entitlements.

## Deployment notes

TBD. The target is AWS: CloudFront, WAF, ALB, RDS PostgreSQL, S3, ElastiCache and CloudWatch. `config.settings.prod` expects TLS to be terminated at the ALB (`X-Forwarded-Proto`), and `requirements/prod.txt` includes gunicorn.
