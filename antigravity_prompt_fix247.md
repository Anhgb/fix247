# Prompt Antigravity – Xây dựng Fix 24/7 (Web App MVP)

## Cách dùng (đọc trước)

1. Tạo thư mục dự án `fix247/`, mở bằng Antigravity.
2. Xuất **PRD** và **SRS** từ Claude Docs sang Markdown, lưu thành `docs/PRD.md` và `docs/SRS.md` trong thư mục dự án.
3. Tạo file `AGENTS.md` ở thư mục gốc, dán nội dung **Phần 1 (Quy tắc dự án)**. Antigravity sẽ dùng làm rule cho mọi phiên.
4. Mở Agent Manager, chọn chế độ **Planning**, dán **Phần 2 (Prompt khởi động)**.
5. Duyệt kế hoạch (Implementation Plan) rồi cho chạy. Sau khi xong mỗi giai đoạn, dán tiếp prompt giai đoạn kế tiếp ở **Phần 3**. Không dán tất cả một lần.
6. Cuối mỗi giai đoạn, tự chạy app, thử luồng chính, rồi mới sang giai đoạn sau.

> Gợi ý: dùng model mạnh nhất cho giai đoạn 0, 1 và 3 (kiến trúc, điều phối thợ); model nhanh hơn cho giao diện.

---

## Phần 1 – `AGENTS.md` (quy tắc dự án)

```markdown
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
```

---

## Phần 2 – Prompt khởi động (dán vào Agent Manager)

```text
You are a senior full-stack engineer and tech lead. Build "Fix 24/7": an AI-assisted repair marketplace web app (PWA) for motorbike and home-appliance repair in Hue, Vietnam. Customers describe a fault with photos/audio/text, get an AI diagnosis with a reference price range, then book the nearest technician (emergency by GPS, or scheduled). Technicians accept jobs, quote, repair, get paid; admins verify technicians and manage the price catalog. Completed jobs feed a "digital health log" per vehicle/appliance.

READ FIRST, in full: AGENTS.md, docs/PRD.md, docs/SRS.md. They are the source of truth. Follow AGENTS.md strictly.

PHASE 0 – FOUNDATION (do this now, then stop and wait for my review)
1. Read the docs and write docs/DECISIONS.md: list assumptions, ambiguities, and any conflicts between PRD and SRS with your resolution.
2. Produce a complete Implementation Plan for the whole MVP, split into these phases:
   - P0 Foundation (monorepo, docker compose, CI, DB schema + migrations, seed data, auth skeleton, design system)
   - P1 Customer diagnosis flow (UC-02)
   - P2 Booking and dispatch (UC-03, UC-04, UC-05) with order state machine and realtime tracking
   - P3 Payment, completion, reviews, warranty (UC-06, UC-07), commission ledger
   - P4 Technician portal and digital health log (UC-08, UC-09)
   - P5 Admin panel, QR locations, analytics (UC-10, UC-11, UC-12)
   - P6 Hardening: PWA/offline SOS guide, security pass, performance, E2E tests, README and deployment guide
3. Implement ONLY Phase P0:
   - Monorepo scaffold per AGENTS.md, docker-compose with web/api/postgres(postgis)/redis/minio, .env.example
   - Full database schema from SRS section 8 and PRD section 12 as Alembic migrations (UUID PKs, timestamps, soft delete where specified, GIST index on technician location, constraints from SRS 8)
   - Seed script: 2 categories groups (motorbike, home), >= 60 realistic faults in fault_catalog with Vietnamese names and price ranges (labor + parts), 12 demo technicians scattered around Hue (lat 16.46, lng 107.59), demo customers, 1 admin, 3 QR locations (e.g. a dormitory, a parking lot, a rental-room area)
   - Auth: phone + OTP (mock provider prints OTP to console; limits per SRS FR-AUTH-01), JWT access/refresh, role guards (customer, technician, admin), terms-acceptance gate
   - Design system in Tailwind: tokens, Button, Input, Card, Badge, BottomSheet, StatusTimeline, Toast; mobile-first layout; Vietnamese copy; PWA manifest + service worker shell
   - Home page with two large actions: "Xe hỏng giữa đường" and "Sửa tại nhà"
   - Health-check endpoint, structured logging with trace IDs, CI workflow (lint + tests)
4. Verify: docker compose up works from a clean clone, migrations and seed run, OTP login works for all three roles, tests pass. Produce a walkthrough with screenshots of the home page on a mobile viewport.

Constraints: no real API keys exist yet; all integrations must have working mocks. Do not start Phase P1 until I say so.
```

---

## Phần 3 – Prompt từng giai đoạn (dán lần lượt sau khi duyệt giai đoạn trước)

### Giai đoạn P1 – Chẩn đoán AI

```text
Proceed to Phase P1: customer diagnosis flow (UC-02, FR-DIAG-01..09). Re-read SRS sections 3 (UC-02), 4.2 and 7.2.

Build:
- Backend: POST /api/v1/diagnoses (multipart), GET /api/v1/diagnoses/{id}, POST /api/v1/diagnoses/{id}/feedback. Upload validation and limits per FR-DIAG-01; presigned/signed media URLs; per-user and anonymous daily quotas (FR-DIAG-07, return 429); result cache by content hash for 24h (FR-DIAG-08).
- AI adapter with 3 implementations: MockAI (deterministic, picks a fault from the catalog by keywords, default in dev), GeminiAI, OpenAIAI. Strict JSON schema from SRS 7.2, validate, retry up to 2 times, timeout 20s, automatic fallback to the secondary provider, graceful failure path (user can still book without a diagnosis).
- Price mapping: map fault_code to fault_catalog to price_min/price_max (round to 10,000 VND). Unknown fault_code means "Cần thợ khảo sát" and no price.
- Low confidence (<50%): return follow-up questions; UI lets the user answer and re-run.
- Frontend: /diagnose (category picker, camera/photo upload with client-side compression to <= 1.5MB, short video, audio recorder <= 20s, text box, asset picker), loading state with progress, /diagnose/[id] result screen: safety warnings first, top-3 causes with confidence badge (Thấp/Vừa/Cao), severity, self-checks, price range, disclaimer "Kết quả chỉ mang tính tham khảo", Beta label on audio analysis, primary button "Gọi thợ".
- Tests: schema validation, fallback behaviour, quota, cache, price mapping rules.
Acceptance: AT-01 and AT-09 in SRS 10.2 pass. Provide a walkthrough showing a motorbike case and an air-conditioner case end to end using MockAI.
```

### Giai đoạn P2 – Đặt thợ & điều phối

```text
Proceed to Phase P2: booking, dispatch, quote, realtime tracking (UC-03, UC-04, UC-05, FR-BOOK, FR-TRACK, BR-03..07).

Build:
- Order state machine exactly as SRS section 6 in a single module; reject invalid transitions with 409 INVALID_TRANSITION; every transition writes order_events.
- Emergency dispatch: PostGIS ST_DWithin within 3km of online + approved technicians whose location is fresh (<= 2 min); rank by BR-03 formula; invite sequentially with a 60s expiry using Redis + a worker; expand to 5km after 90s; end in NO_TECH with fallback options. Night surcharge per BR-04 shown before confirmation. One open emergency order per customer.
- Scheduled booking: time window rules FR-BOOK-03, technician suggestions or manual pick, reminders 1h before.
- Quote flow: technician submits line items; warn both sides and require a reason when above price_max by > 20% (BR-05); customer accept/reject; reject triggers survey fee per BR-07; cancellation rules BR-06.
- Realtime: WebSocket /orders/{id}/stream for status, technician location (every 10-15s only while ON_THE_WAY), and in-order chat (text + image, phone numbers hidden). Polling fallback every 5s.
- Frontend: /book/[diagnosisId], /orders, /orders/[id] (map with technician position, StatusTimeline, chat, quote approval sheet). Use a MapProvider interface; default implementation OpenStreetMap/Leaflet (no key); Google/Goong can be plugged in later.
- Technician-side minimal screens needed to test: /tech/dashboard (online toggle, incoming job modal with countdown), /tech/orders/[id] (accept, status updates, quote form).
- Tests: state machine (all valid/invalid transitions), dispatch ranking and expansion logic with time mocking, quote threshold, cancellation fees.
Acceptance: AT-02, AT-03, AT-04, AT-10. Include a script `make demo-dispatch` that simulates 12 technicians moving around Hue and a customer emergency order, so I can watch dispatch work.
```

### Giai đoạn P3 – Thanh toán, hoàn thành, đánh giá

```text
Proceed to Phase P3: completion, payment, commission, reviews, warranty (UC-06, UC-07, FR-PAY, FR-RATE, BR-01, BR-02, BR-08, BR-09).

Build:
- Invoice generation (labor, parts, surcharge, total; internal commission line) with exact arithmetic (use integer VND / Decimal).
- Payment methods: cash (technician confirms collected, customer confirms), VietQR dynamic QR, wallet via a PaymentProvider interface with MockProvider default; webhook endpoint with signature verification and idempotency by provider_ref.
- Completion: technician marks done with after-photos; customer confirms or auto-confirm after 24h via a scheduled job (every 10 min); disputes move to DISPUTED.
- Commission ledger: default 10% (configurable 8-12%), surcharge excluded; technician debt tracking, weekly settlement view, block new jobs when debt > 500,000 VND or overdue 7 days (BR-09).
- Reviews: customer 1-5 stars + tags + comment (<= 500 chars) only for COMPLETED orders, one per side; technician-to-customer private rating; time-weighted technician rating; auto-suspension rules FR-TECH-05.
- Warranty claims: 7 days (motorbike) / 30 days (home), with photos, notifies technician.
- Frontend: payment screen, invoice view, confirmation, review form, warranty request, technician wallet.
- Tests: invoice totals, commission, auto-confirm job, webhook idempotency (send twice, recorded once), debt blocking, review constraints.
Acceptance: AT-05, AT-06.
```

### Giai đoạn P4 – Cổng thợ & hồ sơ sức khỏe số

```text
Proceed to Phase P4: technician portal completion and Digital Health Log (UC-08, UC-09, FR-TECH, FR-HEALTH).

Build:
- Technician onboarding: profile, ID number (encrypted), portrait and certificate uploads, categories, service area; status PENDING/APPROVED/REJECTED/SUSPENDED; only APPROVED can go online; auto-offline after 5 minutes without location pings.
- Technician wallet and history, earnings, rating and badges.
- Assets: CRUD for vehicles/appliances (max 10 per user, unique plate/serial per user); asset picker integrated into diagnosis and booking.
- Maintenance log automatically created when an order becomes COMPLETED (within 1 minute), maintenance reminders by rule (time or km) delivered via a NotificationService interface (web push + SMS mocks), asset detail page with timeline.
- Optional DIAG-9 feedback: technician labels diagnosis correct/incorrect/partial after the job; store in diagnoses.verified_label and expose accuracy on the admin dashboard later.
- Tests and a walkthrough covering: onboarding to approval to first job to log appears in the customer's asset timeline.
```

### Giai đoạn P5 – Admin, QR, thống kê

```text
Proceed to Phase P5: admin panel, QR locations, analytics (UC-10, UC-11, UC-12, FR-ADM, FR-QR).

Build:
- Admin app under /admin with role guard: technician review queue (approve/reject/suspend with reason and audit log), fault_catalog CRUD with CSV import and versioning (changes never alter existing orders), order explorer with intervention (change status via the state machine, reassign, cancel, notes), dispute resolution and refunds, settings (commission, surcharge, radius, AI quota, survey fee) effective for new orders only, QR location manager that generates printable QR codes (URL /qr/{code}, >= 10 random chars) with scan and order stats.
- Customer QR landing: /qr/[code] prefills address and opens the booking/diagnosis flow without installing anything; invalid code returns 404.
- Dashboard: orders, GMV, commission, median time-to-accept, completion rate, dispute rate, AI top-3 accuracy (from verified labels), cost per AI call and daily AI/maps spend with alert at 80% of the monthly budget.
- Admin action audit log on every mutating admin endpoint.
Acceptance: AT-07, AT-08; admin can complete the full technician onboarding to dispute workflow.
```

### Giai đoạn P6 – Hoàn thiện & bàn giao

```text
Proceed to Phase P6: hardening and handover.

Do:
- PWA: installable, cached home + /sos-guide (static basic rescue guide + one-tap call to hotline) working offline; Lighthouse PWA and performance checks, target LCP < 3s on throttled 4G.
- Security pass against OWASP Top 10: authz tests for every endpoint by role, rate limiting (OTP, diagnoses, order creation), file-type validation and malware-safe handling of uploads, CORS/CSRF/headers, secrets scan, dependency audit, PII never in logs.
- Reliability: graceful degradation when AI or maps fail, retry/backoff, idempotent jobs, backups note, structured logs with trace IDs per order.
- Test suite: unit, integration, Playwright E2E covering PRD flows 6.1 (emergency), 6.2 (scheduled), 6.3 (technician), plus the 10 acceptance scenarios AT-01..AT-10; k6 smoke load test (200 concurrent users, 20 orders/min).
- Documentation: README (quick start in 5 commands), docs/ARCHITECTURE.md (diagram + module map), docs/API.md (OpenAPI export), docs/DEPLOYMENT.md (VPS + Docker, env vars, how to switch each mock to a real provider: AI, SMS, maps, push, VietQR/MoMo/VNPay), docs/RUNBOOK.md, and a requirement traceability table (SRS ID to code to test).
- Final report: what is complete, what is mocked, known gaps vs SRS, and a prioritized list of next steps.
```

---

## Phần 4 – Prompt sửa lỗi / mở rộng (dùng khi cần)

**Khi có lỗi:**
```text
Bug: <mô tả>. Steps to reproduce: <các bước>. Expected: <mong đợi>. Actual: <thực tế>.
Find the root cause (do not patch symptoms), add a failing test first, fix it, run the full test suite, and explain the cause and the fix in 3-5 lines. Reference the related SRS requirement ID.
```

**Khi muốn thay mock bằng dịch vụ thật:**
```text
Replace the <AI|SMS|Maps|Push|Payment> mock with a real <provider> implementation behind the existing interface. Keep the mock as the default for local/test. Add required env vars to .env.example, handle errors/timeouts/retries, add contract tests with recorded fixtures, and update docs/DEPLOYMENT.md. Never commit keys.
```

**Khi muốn review chất lượng trước khi demo:**
```text
Act as a strict reviewer. Compare the current codebase against docs/SRS.md section by section. Produce a table: requirement ID, status (done/partial/missing), evidence (file/test), and fix plan. Then fix every item marked partial or missing that belongs to the MVP, run all tests, and update the traceability table.
```
