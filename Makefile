.PHONY: dev stop restart install build build-frontend bundle package web clean

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
build-frontend:
	cd frontend && npm run build

# Bundle frontend into Python package
bundle: build-frontend
	@echo "Bundling frontend into Python package..."
	@rm -rf src/amplifier_playground/web/static
	@mkdir -p src/amplifier_playground/web/static
	@cp -r frontend/dist/* src/amplifier_playground/web/static/
	@echo "Frontend bundled to src/amplifier_playground/web/static/"

# Build distributable package (includes frontend)
package: bundle
	@echo "Building Python package..."
	uv build
	@echo "Package built in dist/"

# Launch the web UI (uses bundled frontend if available)
web:
	uv run amplay

# Run backend only (for development)
backend:
	uv run uvicorn amplifier_playground.web.app:app --reload

# Run frontend only (for development)
frontend:
	cd frontend && npm run dev

# Clean build artifacts
clean:
	rm -rf dist/
	rm -rf src/amplifier_playground/web/static/
	rm -rf frontend/dist/
	rm -rf .ruff_cache/
