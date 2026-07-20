# Contributing

Thanks for your interest in contributing to the AI Opportunity Discovery Agent!

## Getting Started

1. **Fork** the repository and clone your fork.
2. Create a Python 3.11+ virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your keys.
5. Verify everything works:
   ```bash
   python main.py --run-now --mock
   ```

## Making Changes

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes. Keep commits focused and well-described.
3. Test with `--mock` mode to avoid burning API quota:
   ```bash
   python main.py --run-now --mock
   ```
4. Open a Pull Request against `main` with a clear description of what you changed and why.

## Code Style

- Use type hints on all function signatures.
- Keep functions focused — one responsibility each.
- Add docstrings to public functions.
- Follow existing project conventions for naming and structure.

## Adding a New Source

The ingestion pipeline is modular. To add a new data source:

1. Create a new file under `digest_agent/ingestion/` (e.g., `my_source.py`).
2. Implement an async function that returns a list of `NormalizedItem` objects.
3. Register your function in `digest_agent/ingestion/pipeline.py`.
4. Add mock data support for testing without network calls.

## Reporting Issues

Open a GitHub Issue with:
- A clear description of the problem or feature request.
- Steps to reproduce (if applicable).
- Your Python version and OS.
