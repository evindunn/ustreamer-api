---
name: ustreamer-api-doc-sync
description: Update the root README documentation for the ustreamer_api app when API routes, CLI entrypoints, or environment variables change. Use this when settings.py, routes.py, _cli.py, compose.yaml, or nginx.conf change and the docs tables need to be refreshed.
---

# ustreamer API Doc Sync

Use this skill to refresh the repository documentation for the `ustreamer_api` app.

## What to update

Update [README.md](/Users/edunn/repos/docker/ustreamer/README.md) with:

- env var tables for each app entrypoint
- API route tables
- short usage notes needed to explain nginx/API path prefixes

## Source of truth

Read these files before editing docs:

- [ustreamer_api/ustreamer_api/settings.py](/Users/edunn/repos/docker/ustreamer/ustreamer_api/ustreamer_api/settings.py)
- [ustreamer_api/ustreamer_api/routes.py](/Users/edunn/repos/docker/ustreamer/ustreamer_api/ustreamer_api/routes.py)
- [ustreamer_api/ustreamer_api/_cli.py](/Users/edunn/repos/docker/ustreamer/ustreamer_api/ustreamer_api/_cli.py)
- [compose.yaml](/Users/edunn/repos/docker/ustreamer/compose.yaml)
- [nginx.conf](/Users/edunn/repos/docker/ustreamer/nginx.conf)

## Env var mapping

Document env vars by entrypoint:

- API server:
  `APISettings` fields and `USTREAMER_API_` prefix
- Worker:
  `WorkerSettings` fields and `USTREAMER_WORKER_` prefix
- CLI client:
  env vars read directly in `_cli.py`, such as `USTREAMER_CA_CERTS`

Use tables with exactly these columns:

| Variable | Description | Default |
| --- | --- | --- |

## Route mapping

Document routes from `routes.py` using a table with exactly these columns:

| Method | Path | Description |
| --- | --- | --- |

Use the application route path from FastAPI. If nginx adds a public prefix like `/api`, mention that in prose near the table instead of changing the table path values.

## Defaults

- For `pathlib.Path` defaults derived from `_default_data_dir()`, document the effective default path as `./.ustreamer-data`.
- For unset optional env vars read via `os.environ.get`, document the default as `unset`.
- Preserve concise wording taken from field descriptions and route docstrings when possible.

## Workflow

1. Read the source-of-truth files.
2. Extract env vars, descriptions, and defaults.
3. Extract HTTP methods, paths, and route descriptions.
4. Update the root README tables.
5. Keep the docs compact and avoid duplicating implementation details.
