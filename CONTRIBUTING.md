# Contributing

## Setup
```bash
make install
cp .env.example .env
```

## Quality gates
- `make lint` (ruff on `src`, `tests`, and `evaluation/resume_metrics.py`)
- `make typecheck` (mypy on the same maintained paths)
- `make test` (pytest)

CI runs three separate jobs:
- `lint` on Python 3.11
- `typecheck` on Python 3.11
- `test` on Python 3.10 and 3.11 with `fail-fast: false`

To reproduce the GitHub Actions pipeline locally from a clean checkout:
```bash
make install
make lint
make typecheck
.venv/bin/pytest --cov=src --cov-report=term-missing --cov-fail-under=50 -q
```

## Expectations
- Keep behavior config-driven.
- Add tests for new logic.
- Prefer simple, explicit code over framework magic.
