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
