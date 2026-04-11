# ustreamer-api

## Install dependencies

Install the app and development dependencies with Poetry:

```bash
poetry install --with dev
```

## Run the server

Start the FastAPI app with Uvicorn:

```bash
poetry run uvicorn --factory 'ustreamer_api:create_app' --reload
```

By default, the server will be available at `http://127.0.0.1:8000`.

## Run tests

Run the test suite with coverage reporting:

```bash
poetry run test
```

This prints a terminal coverage report for the `ustreamer_api` package.
