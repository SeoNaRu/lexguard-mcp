# Repository Guidelines

## Project Structure & Module Organization

This repository is a Python MCP server for Korean legal data. Core application code lives under `src/`:

- `src/main.py` initializes the FastAPI app and Streamable HTTP MCP server.
- `src/routes/` contains HTTP/MCP route registration, tool schemas, and tool handlers.
- `src/services/` owns orchestration and business workflows.
- `src/repositories/` wraps external law.go.kr DRF API access.
- `src/utils/` contains response formatting, normalization, retries, masking, and parsing helpers.
- `tests/` contains pytest regression and unit tests, with API fixtures under `tests/fixtures/`.
- `prompts/`, `resources/`, `sample/`, and `api_crawler/` hold prompt templates, MCP resources, sample documents, and API metadata.

## Build, Test, and Development Commands

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the local MCP server on port `9099`:

```bash
python -m src.main
```

Run the full test suite:

```bash
pytest tests/ --tb=short
```

Run focused tests while developing:

```bash
pytest tests/test_local_ordinance_parsing.py -v --tb=short
```

Docker run path:

```bash
docker build -t lexguard-mcp .
docker run -p 9099:9099 lexguard-mcp
```

## Coding Style & Naming Conventions

Use Python 3.11+ and 4-space indentation. Keep modules aligned with the existing layered architecture: routes call services, services call repositories, and shared formatting/parsing belongs in `src/utils/`. Prefer explicit, descriptive names such as `local_ordinance_tool`, `LawComparisonService`, and `test_*_html_response`. Text files should use LF line endings as configured by `.gitattributes` and `.editorconfig`.

## Testing Guidelines

Tests use `pytest` and `pytest-asyncio`. Add focused regression tests for every bug fix, especially API parsing, error response shape, `_meta` fields, and key masking. Name test files `tests/test_<feature>.py` and test functions `test_<expected_behavior>`. Mock external API calls unless the test is explicitly marked or documented as integration-like.

## Commit & Pull Request Guidelines

Recent history uses concise conventional-style prefixes, for example `fix(local-ordinance): ...`, `fix(response-formatter): ...`, and `chore: ...`. Keep commits scoped to one logical change and include tests in the same commit when relevant. PRs should summarize the issue, describe the fix, list test commands/results, and mention any live verification or API behavior changes.

## Security & Configuration Tips

Copy environment values from `env.example` or `.env.example`; do not commit real secrets. `LAW_API_KEY` is used as the law.go.kr `OC` parameter and must stay masked in logs and responses. Verify masking when changing repository, formatter, or error-handling code.
