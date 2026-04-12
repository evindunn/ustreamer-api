# ustreamer-api

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

## Run tests

Run the test suite with coverage reporting:

```bash
poetry run test
```

This prints a terminal coverage report for the `ustreamer_api` package.
