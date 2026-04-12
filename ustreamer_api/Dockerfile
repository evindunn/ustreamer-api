FROM git.localdomain.net/docker/images/debian:trixie-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_CACHE_DIR=/tmp/pip_cache

WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
    && apt-get install --yes --no-install-recommends python3-pip python3-venv

COPY pyproject.toml README.md ./
COPY ustreamer_api ./ustreamer_api

RUN --mount=type=cache,target=/tmp/pip_cache,sharing=locked \
    python3 -m venv /opt/venv \
    && . /opt/venv/bin/activate \
    && pip install . \
    && ln -s /opt/venv/bin/ustreamer-api /usr/local/bin/ustreamer-api

EXPOSE 8000

CMD ["ustreamer-api", "serve", "--host", "0.0.0.0", "--port", "8000"]
