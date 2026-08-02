# Root Makefile for Praesagus deployment and development

.PHONY: all setup user-build ingestion-build user-up user-down ingestion-up ingestion-down clean

all: user-build

setup: user-build
	@echo "Praesagus user-facing services are built and ready."

user-build:
	@echo "Building user-facing frontend and backend containers..."
	docker compose -f docker-compose.user.yml build

ingestion-build:
	@echo "Building ingestion-only containers..."
	docker compose -f docker-compose.ingest.yml build

user-up:
	@echo "Starting user-facing frontend and backend services..."
	docker compose -f docker-compose.user.yml up --build

user-down:
	docker compose -f docker-compose.user.yml down

ingestion-up:
	@echo "Starting ingestion services in the separate pipeline..."
	docker compose -f docker-compose.ingest.yml up --build

ingestion-down:
	docker compose -f docker-compose.ingest.yml down

sec-qr-report:
	@echo "Running SEC QR report. Set SERPAPI_KEY in the environment to enable Google AI overview fallback."
	python scripts/sec_qr_report.py --companies AAPL:0000320193 MSFT:0000789019 --forms 10-Q 8-K --out /tmp/sec_reports --interval 300 --summarize --use-serpapi

clean:
	rm -rf frontend/node_modules frontend/dist
	@echo "Cleaned frontend build artifacts."
