.PHONY: dev stop restart install build

# Start development servers (frontend + backend)
dev:
	@./scripts/dev.sh start

# Stop development servers
stop:
	@./scripts/dev.sh stop

# Restart development servers
restart:
	@./scripts/dev.sh restart

# Install dependencies
install:
	uv sync
	cd frontend && npm install

# Build frontend for production
build:
	cd frontend && npm run build

# Run backend only
backend:
	uv run uvicorn amplifier_workbench.web.app:app --reload

# Run frontend only
frontend:
	cd frontend && npm run dev
