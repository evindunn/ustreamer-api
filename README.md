# ustreamer API

This repository contains `ustreamer_api`: a FastAPI service, background worker, and CLI for managing uStreamer-backed timelapses.

### API server env vars

| Variable | Description | Default |
| --- | --- | --- |
| `USTREAMER_DATA_DIR` | Directory to store application data, such as the database file and timelapse images/videos. | `./.ustreamer-data` |
| `USTREAMER_DB_FILE` | Path to the database file. If set to `:memory:`, an in-memory database will be used. | `:memory:` |

### Worker env vars

| Variable | Description | Default |
| --- | --- | --- |
| `USTREAMER_DATA_DIR` | Directory to store application data, such as the database file and timelapse images/videos. | `./.ustreamer-data` |
| `USTREAMER_DB_FILE` | Path to the database file. If set to `:memory:`, an in-memory database will be used. | `:memory:` |
| `USTREAMER_WORKER_USTREAMER_URL` | Base URL of the uStreamer instance to control. | `http://127.0.0.1:8080` |
| `USTREAMER_WORKER_LOG_LEVEL` | Worker log level. | `INFO` |

### CLI client env vars

| Variable | Description | Default |
| --- | --- | --- |
| `USTREAMER_API_BASE_URL` | Base URL used by `ustreamer-api client` commands. | `https://picam.localdomain.net/api` |
| `USTREAMER_CA_CERTS` | Comma-separated list of CA certificate files trusted by `ustreamer-api client create`. | unset |

### API routes

The FastAPI application routes are mounted at `/`.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/healthz` | Return a simple health status payload. |
| `GET` | `/timelapses` | Return timelapses sorted by start time with pagination. |
| `GET` | `/timelapses/{timelapse_id}` | Return a single timelapse by id. |
| `GET` | `/timelapses/{timelapse_id}/video` | Return the rendered video for a completed timelapse. |
| `DELETE` | `/timelapses/{timelapse_id}` | Delete a timelapse and any generated on-disk resources. |
| `POST` | `/timelapses` | Create and persist a new timelapse record. |

See `/docs` for more details.

# Development

## Install dependencies

Install the app and development dependencies with Poetry:

```bash
poetry install --with dev
```

## CLI demo

Use the Click CLI to run the API server:

```bash
poetry run ustreamer-api serve --reload
```

By default, the server will be available at `http://127.0.0.1:8000`.

Run the background worker in a separate terminal:

```bash
poetry run ustreamer-api worker
```

Point the worker at a non-default uStreamer instance with `USTREAMER_WORKER_USTREAMER_URL` if needed.

You can also override the bind address for the API server:

```bash
poetry run ustreamer-api serve --host 0.0.0.0 --port 8000
```

For local CLI use, set `USTREAMER_API_BASE_URL=http://127.0.0.1:8000` before running `ustreamer-api client ...`.

Dump the generated OpenAPI schema to stdout:

```bash
poetry run ustreamer-api openapi
```

## Run tests

Run the test suite with coverage reporting:

```bash
poetry run test
```

This prints a terminal coverage report for the `ustreamer_api` package.
