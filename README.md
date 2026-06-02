# tax-gpt

A web-based Austrian income-tax preparation assistant.

It stores multi-user tax workspaces in SQLite, supports tax years from 2025 onward,
lets users enter income and deduction data, uploads invoices/documents, and can ask
Ollama at `192.168.1.163:11434` to classify documents into Austrian tax categories.
The final view produces a FinanzOnline-oriented summary that you can use while
filling L1/E1 sections.

This is preparation software, not tax advice. Always verify eligibility, caps,
self-retention, third-party transmitted data, and year-specific FinanzOnline field
names before filing.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[test]"
flask --app taxgpt run --debug
```

Open http://127.0.0.1:5000 and create the first user.

Useful environment variables:

```bash
export SECRET_KEY="replace-me"
export DATABASE_URL="sqlite:////absolute/path/taxgpt.sqlite3"
export UPLOAD_FOLDER="/absolute/path/uploads"
export OLLAMA_BASE_URL="http://192.168.1.163:11434"
export OLLAMA_MODEL="llama3.1:latest"
export OLLAMA_VISION_MODEL="minicpm-v:latest"
```

## Docker

```bash
docker compose up --build
```

The container listens on http://127.0.0.1:8000 and persists the SQLite database
and uploads in the `tax_gpt_data` volume.

## Tests

```bash
pytest
```

## Releases and image publishing

The project version lives in `VERSION`, `pyproject.toml`, and `taxgpt.__version__`.
Tests check that the version is semantic versioning and in sync.

The GitHub Actions workflow:

- runs tests on pull requests and pushes
- validates semantic versioning
- builds and pushes `adcrinis/tax-gpt` to Docker Hub on pushes to `main` or tags
- pushes tags for `latest`, the semantic version, semver tags from `vX.Y.Z`, and
  the commit SHA

Required GitHub secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

Tag a release with the same version:

```bash
git tag v0.1.0
git push origin v0.1.0
```
