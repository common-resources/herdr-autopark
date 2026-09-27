# `make check` is what CI runs. Tools come through uvx, so nothing is installed into the repo.
PY := bin/autopark bin/parked-view bin/harnesses.py bin/test_autopark.py
SH := bin/parked-wait bin/setup.sh bin/open-pane.sh
SHFMT := uvx --from shfmt-py shfmt -i 2 -ci
RUFF := uvx ruff

.PHONY: check lint test fmt
check: lint test

lint:
	$(RUFF) check
	$(RUFF) format --check
	uvx --from shellcheck-py shellcheck $(SH)
	$(SHFMT) -d $(SH)

test:
	python3 bin/test_autopark.py

# Formats through a temp file and rename: a parked pane's bash is still reading parked-wait
# from disk, and an in-place rewrite would change the bytes under it.
fmt:
	$(RUFF) check --fix
	$(RUFF) format
	for f in $(SH); do $(SHFMT) "$$f" > "$$f.tmp" && chmod --reference="$$f" "$$f.tmp" && mv "$$f.tmp" "$$f"; done
