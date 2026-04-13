FROM git.localdomain.net/docker/images/debian:trixie-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
    && apt-get install --yes --no-install-recommends python3-pip python3-venv

FROM base AS build

WORKDIR /build

COPY pyproject.toml poetry.lock README.md ./
COPY ustreamer_api ./ustreamer_api

ENV PIP_CACHE_DIR=/tmp/pip_cache
RUN --mount=type=cache,target=/tmp/pip_cache,sharing=locked \
    python3 -m pip wheel --wheel-dir /dist .

FROM base

WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
    && apt-get install --yes --no-install-recommends ffmpeg

COPY --from=build /dist /tmp/dist

ENV PIP_CACHE_DIR=/tmp/pip_cache
RUN --mount=type=cache,target=/tmp/pip_cache,sharing=locked \
    python3 -m venv /opt/venv \
    && . /opt/venv/bin/activate \
    && pip install /tmp/dist/*.whl \
    && rm -rf /tmp/dist \
    && ln -s /opt/venv/bin/ustreamer-api /usr/local/bin/ustreamer-api

EXPOSE 8000

CMD ["ustreamer-api", "serve", "--host", "0.0.0.0", "--port", "8000"]
