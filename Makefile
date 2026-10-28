.PHONY: demo-dispatch dev-api dev-web test-backend test-p2

demo-dispatch:
	python scripts/demo_dispatch.py

dev-api:
	cd apps/api && .venv/Scripts/uvicorn app.main:app --reload --port 8000

dev-web:
	cd apps/web && npm run dev

test-backend:
	cd apps/api && .venv/Scripts/pytest tests/ -v

test-state-machine:
	cd apps/api && .venv/Scripts/pytest tests/test_order_state_machine.py -v

test-dispatch:
	cd apps/api && .venv/Scripts/pytest tests/test_dispatch.py -v

test-quote:
	cd apps/api && .venv/Scripts/pytest tests/test_quote.py -v

test-p2:
	cd apps/api && .venv/Scripts/pytest tests/test_order_state_machine.py tests/test_dispatch.py tests/test_quote.py tests/test_cancellation.py -v

