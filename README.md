# ustreamer with Docker Compose

This setup runs [`pikvm/ustreamer`](https://github.com/pikvm/ustreamer) behind Nginx in Docker Compose and exposes HTTPS on port `443` by default.

## 1. Configure

Copy the example environment file:

```bash
cp .env.example .env
```

If your camera is not `/dev/video0`, update `VIDEO_DEVICE` in `.env`.

## 2. Start

```bash
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
| `USTREAMER_API_DATA_DIR` | Directory used for API-managed data such as the SQLite database. | `./.ustreamer-data` |
| `USTREAMER_API_DB_FILE` | SQLite database path for the API server. | `:memory:` |

### Worker env vars

| Variable | Description | Default |
| --- | --- | --- |
| `USTREAMER_WORKER_DATA_DIR` | Directory used to store worker output such as captured frames. | `./.ustreamer-data` |
| `USTREAMER_WORKER_DB_FILE` | SQLite database path for the worker. | `:memory:` |
| `USTREAMER_WORKER_USTREAMER_URL` | Base URL used by the worker to fetch snapshots from uStreamer. | `http://127.0.0.1:8080` |
| `USTREAMER_WORKER_LOG_LEVEL` | Worker log level. | `INFO` |

### CLI client env vars

| Variable | Description | Default |
| --- | --- | --- |
| `USTREAMER_CA_CERTS` | Comma-separated list of CA certificate files trusted by `ustreamer-api client create`. | unset |

### API routes

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/healthz` | Return a simple health status payload. |
| `POST` | `/timelapses` | Create and persist a new timelapse record. |

## 4. Check the camera on the host

```bash
ls /dev/video*
v4l2-ctl --list-devices
```

## Notes

- The container maps the host video device directly, so this is intended for Linux hosts with V4L2 camera devices.
- `ustreamer` listens on `127.0.0.1:8080` by default, so the Compose file forces `--host=0.0.0.0` for container access.
- Common settings can be changed with `.env`: `HTTPS_PORT`, `RESOLUTION`, `FPS`, and `QUALITY`.
- The `vault-agent` and `nginx` services share the `ssl` volume. Certificates are available inside the proxy container at `/secrets/cert.crt`, `/secrets/cert.key`, and `/secrets/ca.crt`.
- `ustreamer` does not terminate TLS here; Nginx handles HTTPS and proxies traffic to `ustreamer` over the internal Compose network.
