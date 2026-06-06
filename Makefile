.PHONY: install dev test backend frontend

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

dev:
	$(MAKE) -j2 backend frontend

backend:
	cd backend && uvicorn app.main:app --reload --port 8765

frontend:
	cd frontend && npm run dev

test:
	cd backend && pytest -v
