# Memoir Agent Skills — developer tasks

.PHONY: all validate lint detect help

all: validate lint

help:
	@echo "make validate  - run repo validator (skills, manifest, links, layout)"
	@echo "make lint      - shell syntax check (+ shellcheck if installed)"
	@echo "make detect    - run the read-only runtime detector"
	@echo "make all       - validate + lint"

validate:
	python3 scripts/validate.py

lint:
	sh -n deployment/detect-runtime.sh
	@command -v shellcheck >/dev/null 2>&1 \
		&& shellcheck deployment/detect-runtime.sh \
		|| echo "shellcheck not installed; skipped (CI runs it)"

detect:
	sh deployment/detect-runtime.sh
