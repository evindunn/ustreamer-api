# ustreamer with Docker Compose

This setup runs [`pikvm/ustreamer`](https://github.com/pikvm/ustreamer) behind Nginx in Docker Compose and exposes HTTPS on port `443` by default.

## 1. Configure

Copy the example environment file:

```bash
cp .env.example deploy/.env
```

If your camera is not `/dev/video0`, update `VIDEO_DEVICE` in `deploy/.env`.

## 2. Start

```bash
cd deploy
docker compose up -d
```

## 3. Open the stream

- Stream: `https://localhost/stream`
- Web UI: `https://localhost/`

## ustreamer-api

When deployed through Nginx, the API is exposed under `https://picam.localdomain.net/api`.

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
| `USTREAMER_CA_CERTS` | Comma-separated list of CA certificate files trusted by `ustreamer-api client create`. | unset |

### API routes

The FastAPI application routes are mounted at `/` internally and exposed publicly under `/api` by Nginx.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/healthz` | Return a simple health status payload. |
| `GET` | `/timelapses` | Return timelapses sorted by start time with pagination. |
| `GET` | `/timelapses/{timelapse_id}` | Return a single timelapse by id. |
| `GET` | `/timelapses/{timelapse_id}/video` | Return the rendered video for a completed timelapse. |
| `DELETE` | `/timelapses/{timelapse_id}` | Delete a timelapse and any generated on-disk resources. |
| `POST` | `/timelapses` | Create and persist a new timelapse record. |

## 4. Check the camera on the host

```bash
ls /dev/video*
v4l2-ctl --list-devices
```

## Notes

- The container maps the host video device directly, so this is intended for Linux hosts with V4L2 camera devices.
- `ustreamer` listens on `127.0.0.1:8080` by default, so the Compose file forces `--host=0.0.0.0` for container access.
- Common settings can be changed with `deploy/.env`: `HTTPS_PORT`, `RESOLUTION`, `FPS`, and `QUALITY`.
- The `vault-agent` and `nginx` services share the `ssl` volume. Certificates are available inside the proxy container at `/secrets/cert.crt`, `/secrets/cert.key`, and `/secrets/ca.crt`.
- `ustreamer` does not terminate TLS here; Nginx handles HTTPS and proxies traffic to `ustreamer` over the internal Compose network.

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

You can also override the bind address for the API server:

```bash
poetry run ustreamer-api serve --host 0.0.0.0 --port 8000
```

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
