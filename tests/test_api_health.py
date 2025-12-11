from fastapi.testclient import TestClient

from src.api.app import app
from src.service.tasks import task_runner


def test_liveness_endpoint_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health/liveness")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["data"]["probe"] == "liveness"


def test_readiness_payload_shape() -> None:
    with TestClient(app) as client:
        response = client.get("/health/readiness")

    body = response.json()
    assert body["status"] == "ok"
    assert body["data"]["probe"] == "readiness"
    assert "cline_cli_available" in body["data"]
    assert "task_worker_running" in body["data"]

    # Status code reflects readiness; both 200 and 503 are acceptable depending
    # on whether CLINE CLI is installed.
    assert response.status_code in (200, 503)


def test_tasks_endpoint_requires_cli() -> None:
    if task_runner.cli_available:
        # Avoid spawning real CLINE CLI in tests.
        return

    with TestClient(app) as client:
        response = client.post(
            "/tasks",
            json={
                "task_id": "test-task-id",
                "repo_url": "https://example.com/repo.git",
                "base_branch": "main",
            },
        )

    assert response.status_code == 503
