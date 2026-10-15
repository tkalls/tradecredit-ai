# AGENTS.md: TradeCredit AI

Shared instructions for every AI coding tool used in this repo (Claude Code, Cursor, others).

## What this project is

TradeCredit AI is a 16-week internship project (12 Oct 2026 to 29 Jan 2027). A borrower (an importer) uploads a
synthetic import-finance application pack. The API saves it and returns `202` + a job id. A background worker
parses, extracts (LLM to JSON), scores (deterministic scorecard) and decides (RAG-grounded credit memo).
Output: **Fund / Refer / Decline** with a cited memo. A human reviewer can override.

The engineer is **Tobi** (intern). Tobi reviews and merges every PR (AI review agents assist; the mentor
gets highlights). Tobi must be able to explain and defend every line in review and in the final presentation.

## Learning mode (read this first)

This is a learning project, so AI help is split in two:

**Tobi writes it. You explain, propose and review:**
- Domain entities, the application state machine, scorecard rules
- Repositories, Unit of Work, services (use cases)
- Pipeline stages (parse, extract, score, decide), prompts, extraction schemas
- RAG: chunking, retrieval, reranking, citation checks
- Eval logic and metrics

For these: explain the concept, sketch the interface or approach, point to the reading, then review Tobi's code
and suggest tests. Only write a full implementation when Tobi explicitly says "write it", and then explain it
line by line.

**You may generate freely (and explain what you did):**
- Config and boilerplate: Docker, Compose, CI workflows, linters, pre-commit, pyproject
- Test scaffolding, fixtures, fakes, synthetic data generators
- Frontend styling and layout
- Formatting of docs Tobi has drafted

**Always:**
- Never commit, push, rebase or open PRs. Tobi does all Git work.
- Keep any change under ~400 lines and to one concern.
- When unsure whether something is "core", ask.

## Hard rules

1. **Synthetic data only.** Never real people, companies, documents or personal data.
2. **The LLM never makes the credit decision.** It extracts fields and writes the memo. The scorecard
   (plain, unit-tested Python) decides. The LLM never changes a score.
3. **No agent frameworks** (LangChain, LlamaIndex) until the Week 10 comparison. Use SDKs directly.
4. **Secrets** live only in `.env` (git-ignored) or the host's secret store. Never print, log or commit keys.

## Architecture rules

- Layering: `api/ -> services/ -> domain/`. `adapters/` implement ports (Protocols) defined in `domain/`.
  Imports never point the other way (enforced by import-linter in CI).
- Ports: `LLMProvider`, `Embedder`, `FileStorage`, `DocumentParser`. Each has a real adapter and a fake for tests.
- Repository pattern: services call `repo.get(id)` / `repo.save(x)`, never raw SQL. SQLAlchemy repos in prod,
  in-memory repos in unit tests. A Unit of Work wraps each request.
- State machine: `RECEIVED -> PARSING -> EXTRACTING -> SCORING -> DECIDING -> DECIDED | NEEDS_REVIEW | FAILED`.
  Every transition is written to an append-only audit log.
- Sync for fast user-facing calls (< 200 ms). Async queue + worker for anything calling outside APIs.
  Jobs must be idempotent (idempotency keys), retried with exponential backoff, and dead-lettered on repeated failure.

## Stack

Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 + Alembic, PostgreSQL 16 + pgvector, Redis + Celery,
S3-compatible storage (MinIO locally), Anthropic SDK (Claude), Voyage AI, PyMuPDF, Langfuse,
Next.js + TypeScript + TanStack Query + Tailwind, Clerk, structlog + OpenTelemetry + Sentry,
pytest + Testcontainers + Playwright, GitHub Actions. Package manager: `uv`.

## Conventions

- Branches: `feat/...`, `fix/...`, `chore/...`, `docs/...` from `main`; merged within 1 to 2 days.
- Commits: Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`), explaining *why*.
- Every behaviour change ships with tests. Type hints everywhere; mypy must pass.
- Decisions with a real alternative get an ADR in `docs/adr/` (copy `0000-template.md`).

## Where things are

- `backend/app/` api, services, domain, adapters, workers
- `backend/tests/` unit, integration, evals
- `docs/design.md` living design doc, `docs/domain.md` import-finance glossary, `docs/adr/` decisions
- `playground/` Weeks 1 to 2 Basics track exercises (not production code)
- `data/synthetic/` generated applications and credit policy (never real data)

## Commands

Fill in as they exist:
- Run tests: `TBD`
- Lint/format: `TBD`
- Local stack: `docker compose up` (from Week 2)
