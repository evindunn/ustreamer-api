import json
import ssl

import click.testing

import ustreamer_api._cli
import ustreamer_api.worker.main


class _FakeResponse:
    """Provide a minimal urllib response object for CLI tests."""

    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        """Return the configured response payload."""
        return self.body


def test_serve_invokes_uvicorn(monkeypatch) -> None:
    """Serve command forwards options to uvicorn."""
    runner = click.testing.CliRunner()
    uvicorn_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        ustreamer_api._cli.uvicorn,
        "run",
        lambda app, **kwargs: uvicorn_calls.append({"app": app, **kwargs}),
    )

    result = runner.invoke(
        ustreamer_api._cli.cli,
        ["serve", "--host", "0.0.0.0", "--port", "9000", "--reload"],
    )

    assert result.exit_code == 0
    assert uvicorn_calls == [
        {
            "app": "ustreamer_api.api:create_app",
            "factory": True,
            "host": "0.0.0.0",
            "port": 9000,
            "reload": True,
        }
    ]


def test_worker_invokes_worker_main(monkeypatch) -> None:
    """Worker command dispatches to worker_main."""
    runner = click.testing.CliRunner()
    worker_calls: list[str] = []

    monkeypatch.setattr(
        ustreamer_api.worker.main,
        "worker_main",
        lambda: worker_calls.append("called"),
    )
    monkeypatch.setattr(ustreamer_api._cli, "worker_main", ustreamer_api.worker.main.worker_main)

    result = runner.invoke(ustreamer_api._cli.cli, ["worker"])

    assert result.exit_code == 0
    assert worker_calls == ["called"]


def test_client_create_posts_payload(monkeypatch) -> None:
    """Client create sends the expected request payload."""
    runner = click.testing.CliRunner()
    captured_url: str | None = None
    captured_body: dict[str, object] | None = None
    captured_content_type: str | None = None
    captured_context: object | None = object()

    def _fake_urlopen(request, context=None) -> _FakeResponse:
        """Capture the outgoing request and return a fake response."""
        nonlocal captured_url, captured_body, captured_content_type, captured_context
        captured_url = request.full_url
        captured_body = json.loads(request.data.decode("utf-8"))
        captured_content_type = request.headers["Content-type"]
        captured_context = context
        return _FakeResponse(b'{"id":"1234"}')

    monkeypatch.setattr(ustreamer_api._cli.urllib.request, "urlopen", _fake_urlopen)

    

    result = runner.invoke(
        ustreamer_api._cli.cli,
        [
            "client",
            "create",
            "--event-duration",
            "300",
            "--target-duration",
            "15",
            "--target-fps",
            "30",
        ],
        env={
            "USTREAMER_CA_CERTS": "",
            "USTREAMER_API_BASE_URL": "https://picam.localdomain.net/api",
        },
    )

    assert result.exit_code == 0
    assert result.output.strip() == '{"id":"1234"}'
    assert captured_url == "https://picam.localdomain.net/api/timelapses"
    assert captured_body == {
        "event_duration": 300.0,
        "target_duration": 15.0,
        "target_fps": 30.0,
    }
    assert captured_content_type == "application/json"
    assert captured_context is None


def test_client_list_gets_paginated_timelapses(monkeypatch) -> None:
    """Client list sends the expected paginated list request."""
    runner = click.testing.CliRunner()
    captured_url: str | None = None
    captured_method: str | None = None
    captured_context: object | None = object()

    def _fake_urlopen(request, context=None) -> _FakeResponse:
        """Capture the outgoing request and return a fake response."""
        nonlocal captured_url, captured_method, captured_context
        captured_url = request.full_url
        captured_method = request.get_method()
        captured_context = context
        return _FakeResponse(b'[{"id":"1234"}]')

    monkeypatch.setattr(ustreamer_api._cli.urllib.request, "urlopen", _fake_urlopen)

    result = runner.invoke(
        ustreamer_api._cli.cli,
        [
            "client",
            "list",
            "--limit",
            "5",
            "--offset",
            "10",
        ],
        env={
            "USTREAMER_CA_CERTS": "",
            "USTREAMER_API_BASE_URL": "https://picam.localdomain.net/api",
        },
    )

    assert result.exit_code == 0
    assert result.output.strip() == '[{"id":"1234"}]'
    assert captured_url == "https://picam.localdomain.net/api/timelapses?limit=5&offset=10"
    assert captured_method == "GET"
    assert captured_context is None


def test_client_delete_sends_delete_request(monkeypatch) -> None:
    """Client delete sends the expected delete request."""
    runner = click.testing.CliRunner()
    captured_url: str | None = None
    captured_method: str | None = None
    captured_context: object | None = object()

    def _fake_urlopen(request, context=None) -> _FakeResponse:
        """Capture the outgoing request and return a fake response."""
        nonlocal captured_url, captured_method, captured_context
        captured_url = request.full_url
        captured_method = request.get_method()
        captured_context = context
        return _FakeResponse(b"")

    monkeypatch.setattr(ustreamer_api._cli.urllib.request, "urlopen", _fake_urlopen)

    result = runner.invoke(
        ustreamer_api._cli.cli,
        ["client", "delete", "1234"],
        env={
            "USTREAMER_CA_CERTS": "",
            "USTREAMER_API_BASE_URL": "https://picam.localdomain.net/api",
        },
    )

    assert result.exit_code == 0
    assert result.output.strip() == ""
    assert captured_url == "https://picam.localdomain.net/api/timelapses/1234"
    assert captured_method == "DELETE"
    assert captured_context is None


def test_client_create_loads_ca_certs(monkeypatch, tmp_path) -> None:
    """Client create loads custom CA files into the SSL context."""
    runner = click.testing.CliRunner()
    ca_one = tmp_path / "ca-one.pem"
    ca_two = tmp_path / "ca-two.pem"
    ca_one.write_text("ca-one")
    ca_two.write_text("ca-two")

    loaded_ca_files: list[str] = []

    class _FakeSSLContext:
        """Capture CA-loading operations for the CLI."""

        def load_default_certs(self) -> None:
            """Pretend to load default trust roots."""
            return None

        def load_verify_locations(self, cafile=None, capath=None, cadata=None) -> None:
            """Record each CA file loaded into the trust store."""
            loaded_ca_files.append(cafile)

    ssl_context = _FakeSSLContext()

    monkeypatch.setattr(ustreamer_api._cli.ssl, "create_default_context", lambda: ssl_context)
    monkeypatch.setattr(ustreamer_api._cli.certifi, "where", lambda: "/etc/ssl/certifi.pem")
    monkeypatch.setattr(
        ustreamer_api._cli.urllib.request,
        "urlopen",
        lambda request, context=None: _FakeResponse(b"ok"),
    )

    result = runner.invoke(
        ustreamer_api._cli.cli,
        ["client", "create"],
        env={"USTREAMER_CA_CERTS": f"{ca_one},{ca_two}"},
    )

    assert result.exit_code == 0
    assert loaded_ca_files == ["/etc/ssl/certifi.pem", str(ca_one), str(ca_two)]
