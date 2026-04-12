FROM python:3-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY ustreamer_api ./ustreamer_api

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["ustreamer-api", "serve", "--host", "0.0.0.0", "--port", "8000"]
