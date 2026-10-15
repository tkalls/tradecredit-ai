# TradeCredit AI

A web app that reads a (synthetic) import-finance loan application, extracts its details with an LLM,
scores the borrower with a deterministic scorecard and recommends **Fund, Refer or Decline** with a
credit memo that cites the lending policy. A human reviewer can override every decision.

> Status: Week 0, scaffolding. Built over a 16-week systems design internship (Oct 2026 to Jan 2027).

## Architecture (planned)

Next.js frontend -> FastAPI (validates, enqueues, returns 202 + job id) -> Redis queue -> Celery worker
running Parse -> Extract -> Score -> Decide. Postgres + pgvector for data and embeddings, S3 for raw PDFs.
Claude (extraction, memo) and Voyage AI (embeddings) sit behind adapter ports.

## Run locally

Coming in Week 2 (`docker compose up`).

## Docs

- [Design doc](docs/design.md)
- [Domain glossary](docs/domain.md)
- [Architecture decision records](docs/adr/)
