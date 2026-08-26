# Contributing to TelosVM

First off, thank you for considering contributing to TelosVM! It's people like you that make this the best AI Inference Control Plane in the world.

## Development Setup
1. Fork the repo and clone it locally.
2. Install the elite toolchain:
   ```bash
   pip install -r requirements.txt
   pip install pre-commit
   pre-commit install
   ```
3. Run the test suite to ensure your baseline is clean:
   ```bash
   make test
   ```

## Pull Request Process
1. Ensure your code passes all `pre-commit` hooks (Ruff, Mypy strict, Bandit).
2. Ensure you have maintained >90% test coverage (`pytest --cov=src`).
3. Update the `CHANGELOG.md`.
4. Submit your PR and request review from the CODEOWNERS.

## Architectural Decisions
If you are proposing a major change, please submit an Architecture Decision Record (ADR) in `docs/adr/`.
