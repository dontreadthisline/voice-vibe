.PHONY: frontend dev demo clean help

PORT ?= 8080
HOST ?= localhost

help: ## Show available commands
	@echo "VoiceVibe — Quick Start"
	@echo ""
	@echo "  make frontend [PORT=8080]   Start the Shiny frontend"
	@echo "  make dev    [PORT=8080]     Start frontend in dev/reload mode"
	@echo "  make demo                   Run voice recording demo"
	@echo "  make clean                  Kill all processes on port 8080"
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
clean: ## Kill all processes on port 8080
	@echo "🧹  Cleaning up processes on port 8080..."
	@pids=$$(lsof -ti:8080 2>/dev/null); \
	if [ -n "$$pids" ]; then \
		echo "   Found PIDs: $$pids"; \
		echo "$$pids" | xargs kill -9 2>/dev/null || true; \
		echo "   Killed successfully"; \
	else \
		echo "   No processes found on port 8080"; \
	fi

# ------------------------------------------------------------------
# Shortcut
# ------------------------------------------------------------------
run: frontend ## Alias for 'make frontend'
