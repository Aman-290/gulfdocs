from fastapi.testclient import TestClient
from gulfdocs_api.main import app


def main() -> None:
    with TestClient(app) as client:
        health = client.get("/healthz", headers={"x-request-id": "local-smoke"})
        demo = client.get("/api/v1/demo/documents")
    if health.status_code != 200 or health.json().get("status") != "ok":
        raise SystemExit("API health smoke check failed")
    if demo.status_code != 200 or not demo.json() or demo.json()[0].get("synthetic") is not True:
        raise SystemExit("Public demo smoke check failed")
    print("Local API and synthetic demo smoke checks passed.")


if __name__ == "__main__":
    main()
