import json
import os
from urllib.request import urlopen


def main() -> None:
    api_base_url = os.environ.get("API_BASE_URL", "").rstrip("/")
    if not api_base_url:
        raise SystemExit("API_BASE_URL is required")
    with urlopen(f"{api_base_url}/healthz", timeout=15) as response:  # noqa: S310
        payload = json.load(response)
    if payload.get("status") != "ok":
        raise SystemExit("Production health smoke check failed")
    print("Production API health smoke check passed.")


if __name__ == "__main__":
    main()
