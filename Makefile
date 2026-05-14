.PHONY: frontend dev demo clean help

PORT ?= 8080
HOST ?= 0.0.0.0

help: ## Show available commands
	@echo "VoiceVibe — Quick Start"
	@echo ""
	@echo "  make frontend [PORT=8080]   Start the Shiny frontend"
	@echo "  make dev    [PORT=8080]     Start frontend in dev/reload mode"
	@echo "  make demo                   Run voice recording demo"
	@echo "  make clean                  Kill all residual shiny processes"
	@echo ""

# ------------------------------------------------------------------
# Frontend
# ------------------------------------------------------------------
frontend: clean ## Start the Shiny frontend (auto-kills residual processes)
	@echo "🚀  Starting VoiceVibe frontend on http://$(HOST):$(PORT)"
	@uv run python main.py frontend --host $(HOST) --port $(PORT)

dev: clean ## Start in development mode (auto-reload)
	@echo "🚀  Starting VoiceVibe frontend (dev mode) on http://$(HOST):$(PORT)"
	@uv run python main.py frontend --host $(HOST) --port $(PORT) --reload

# ------------------------------------------------------------------
# Demo
# ------------------------------------------------------------------
demo: ## Run the voice recording + transcription demo
	@uv run python main.py demo

# ------------------------------------------------------------------
# Cleanup
# ------------------------------------------------------------------
clean: ## Kill all residual Shiny / Uvicorn processes
	@echo "🧹  Cleaning up residual processes..."
	@ps aux | grep -E "shiny|uvicorn" | grep -v grep | awk '{print $$2}' | xargs kill -9 2>/dev/null || true
	@sleep 0.5
	@lsof -ti:$(PORT) 2>/dev/null | xargs kill -9 2>/dev/null || true
	@echo "   Done"

# ------------------------------------------------------------------
# Shortcut
# ------------------------------------------------------------------
run: frontend ## Alias for 'make frontend'
