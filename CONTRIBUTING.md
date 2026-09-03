# Contributing

Thanks for considering a contribution! This is a small portfolio/utility
project, but PRs and issues are welcome.

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/or-utilization-tool.git
cd or-utilization-tool
pip install -e ".[dev]"
```

## Before submitting a PR

```bash
ruff check src tests scripts
black src tests scripts
pytest --cov=or_utilization
```

## Guidelines

- Keep functions small and testable; the `metrics.py` and `simulate.py`
  modules are meant to be readable end-to-end without needing outside
  context.
- Any new metric or simulation lever should come with a corresponding test
  in `tests/` using the hand-crafted fixture in `tests/conftest.py`
  (or a new fixture with clearly documented expected values).
- No real patient, surgeon, or hospital data — ever. Sample data must stay
  synthetic (see `scripts/generate_sample_data.py`).
