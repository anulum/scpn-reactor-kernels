# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — local gate entry points

VENV := .venv/bin
PYTHON := $(VENV)/python

.PHONY: venv lint typecheck test validate rust docs preflight

venv:
	python3 -m venv .venv
	$(VENV)/pip install --require-virtualenv -r requirements-dev.txt
	$(VENV)/pip install --require-virtualenv -e ".[cad]"

lint:
	$(VENV)/ruff check .
	$(VENV)/ruff format --check .

typecheck:
	$(VENV)/mypy --strict src tools tests benchmarks

test:
	$(VENV)/pytest -q --cov=src --cov=tools --cov-branch --cov-fail-under=100

validate:
	$(PYTHON) tools/validate_kernels_domain.py kernels-domain.json
	$(PYTHON) tools/generate_kernel_inventory.py --check

rust:
	cd rust && cargo fmt --check && cargo clippy --all-targets --features python -- -D warnings && cargo test

docs:
	$(PYTHON) tools/preflight.py --only docs

preflight:
	$(PYTHON) tools/preflight.py
