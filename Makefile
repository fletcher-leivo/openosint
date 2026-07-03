.PHONY: demo demo-check deploy build test clean

# Record and encode the OpenOSINT web graph demo.
#
# Prerequisites:
#   - node (https://nodejs.org)
#   - ffmpeg  (brew install ffmpeg)
#   - gifski  (brew install gifski)
#   - Web server running: openosint --web  (default http://localhost:8080)
#   - OPENOSINT_DEMO_KEY env var set to your Anthropic API key
#
# Usage:
#   export OPENOSINT_DEMO_KEY=sk-ant-...
#   make demo
#
# See scripts/record-demo/README.md for full operator instructions.

demo: demo-check
	node scripts/record-demo/record.mjs
	bash scripts/record-demo/encode.sh

demo-check:
	@command -v node   >/dev/null 2>&1 || (echo "ERROR: node not found — install from https://nodejs.org"; exit 1)
	@command -v ffmpeg >/dev/null 2>&1 || (echo "ERROR: ffmpeg not found — brew install ffmpeg"; exit 1)
	@command -v gifski >/dev/null 2>&1 || (echo "ERROR: gifski not found — brew install gifski"; exit 1)
	@[ -n "$$OPENOSINT_DEMO_KEY" ] || (echo "ERROR: OPENOSINT_DEMO_KEY is not set"; exit 1)
	@cd scripts/record-demo && npm install --silent
	@cd scripts/record-demo && npx playwright install chromium --quiet 2>&1 | grep -v "Downloading\|[0-9]%" || true
	@echo "[ok] All prerequisites satisfied"

# ─── Service standard targets ────────────────────────────────────────────────

# Deploy: rsync source tree to /srv/openosint (excluding .git, venv, caches, .env)
# and restart the systemd user service.
deploy:
	@echo "[deploy] rsyncing source to /srv/openosint/"
	rsync -a --delete \
		--exclude='.git' \
		--exclude='venv' \
		--exclude='__pycache__' \
		--exclude='*.pyc' \
		--exclude='.env' \
		--exclude='openosint.db' \
		./ /srv/openosint/
	@echo "[deploy] restarting openosint-web.service"
	systemctl --user restart openosint-web.service
	@echo "[deploy] done"

# Build: install/upgrade Python dependencies into the runtime venv.
build:
	@if [ ! -d /srv/openosint/venv ]; then \
		echo "[build] creating venv at /srv/openosint/venv"; \
		/usr/bin/python3.12 -m venv /srv/openosint/venv; \
	fi
	@echo "[build] installing dependencies"
	/srv/openosint/venv/bin/pip install --upgrade pip
	/srv/openosint/venv/bin/pip install -e /srv/openosint/
	@echo "[build] done"

# Test: smoke-test the running web service health endpoint.
test:
	@echo "[test] checking /api/health"
	@curl -fsS http://localhost:8090/api/health && echo "" || (echo "ERROR: health check failed"; exit 1)
	@echo "[test] ok"

# Clean: remove build artifacts and Python caches.
clean:
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	rm -rf build/ *.egg-info openosint.egg-info
	@echo "[clean] done"