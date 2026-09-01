# Memoir Agent Skills — developer tasks

.PHONY: all validate test lint eval bundle dist detect clean help

all: validate test lint eval

help:
	@echo "make validate  - run repo validator (skills, manifest, links, layout)"
	@echo "make test      - run memoir CLI unit tests"
	@echo "make lint      - shell syntax check (+ shellcheck if installed)"
	@echo "make eval      - truth-contract linter against the golden fixture"
	@echo "make bundle    - build skill bundles (tar + claude-plugin + openclaw)"
	@echo "make dist      - stage the bundle and build the wheel"
	@echo "make detect    - run the read-only runtime detector"
	@echo "make all       - validate + test + lint + eval"

test:
	python3 -m unittest discover -s tests

validate:
	python3 scripts/validate.py

lint:
	sh -n deployment/detect-runtime.sh
	@command -v shellcheck >/dev/null 2>&1 \
		&& shellcheck deployment/detect-runtime.sh \
		|| echo "shellcheck not installed; skipped (CI runs it)"

eval:
	@echo "eval: invented-details chapter (must flag)"
	@! ./bin/memoir lint --workspace tests/fixtures/lint \
		--chapters tests/fixtures/lint/chapters \
		--memories tests/fixtures/lint/memories --fail-on unsupported >/dev/null \
		|| (echo "FAIL: linter missed the invented details"; exit 1)
	@echo "eval: faithfully-sourced chapter (must be silent)"
	@./bin/memoir lint --workspace tests/fixtures/lint \
		--chapters tests/fixtures/lint/clean-chapters \
		--memories tests/fixtures/lint/memories --fail-on any >/dev/null
	@echo "eval: OK"

bundle:
	./bin/memoir bundle --format tar --out dist
	./bin/memoir bundle --format claude-plugin --out dist
	./bin/memoir bundle --format openclaw --out dist

dist:
	python3 scripts/stage_bundle.py
	python3 -m build --wheel

clean:
	rm -rf dist build *.egg-info memoir_cli/_skills

detect:
	sh deployment/detect-runtime.sh
