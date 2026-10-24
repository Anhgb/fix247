# Fix 24/7 – Project Rules

## Source of truth
- Requirements: docs/PRD.md (product) and docs/SRS.md (detailed, testable). If they conflict, SRS wins.
- Every feature you implement must reference its requirement IDs (e.g. FR-BOOK-02) in code comments or commit messages.
- Do not invent features outside the MVP scope in PRD section 4. If something is ambiguous, write the assumption into docs/DECISIONS.md and continue.

## Stack (fixed, do not change without asking)
- Frontend: Next.js (App Router) + TypeScript + Tailwind CSS, PWA (manifest + service worker)
- Backend: FastAPI (Python 3.11+), SQLAlchemy 2 + Alembic, Pydantic v2
- DB: PostgreSQL 16 + PostGIS; Redis for queues/cache; WebSocket for realtime
- Storage: S3-compatible (MinIO locally)
- AI: provider-agnostic adapter (Gemini primary, OpenAI fallback), strict JSON schema output
- Local dev: docker compose up must start everything (web, api, db, redis, minio)
- Tests: pytest (backend), Vitest + Playwright (frontend/E2E)

## Engineering rules
- Monorepo: /apps/web, /apps/api, /packages/shared (types), /docs, /infra
- All user-facing text in Vietnamese. Currency VND, dates dd/MM/yyyy, timezone Asia/Ho_Chi_Minh.
- Mobile-first (360–430px), buttons >= 48px, body text >= 16px, WCAG AA contrast.
- Never hardcode secrets. Use .env.example; real keys come from the user.
- Every external service (AI, SMS/OTP, maps, push, payments) sits behind an interface with a mock implementation that is the DEFAULT in dev, so the app runs end-to-end with no API keys.
- Order status changes only go through one state-machine function that enforces the transitions in SRS section 6 and writes order_events.
- AI price rule: prices shown to users ALWAYS come from the fault_catalog table, never from model output.
- Validate all input (Pydantic / zod). Return errors in the SRS 7.4 format.
- Sensitive data (national ID) encrypted at rest; never log PII.
- Write tests for: state machine, commission calculation, dispatch ranking, webhook idempotency, auth/OTP limits.
- Keep functions small, typed, and documented. Run lint + tests before declaring a task done.

## Workflow
- Plan first. For each phase produce an Implementation Plan, then implement, then verify by running the app and tests, then produce a short walkthrough (what works, how to run, what is mocked, known gaps).
- Commit in small steps with conventional commit messages.