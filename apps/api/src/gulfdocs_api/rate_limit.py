from collections import defaultdict, deque
from time import monotonic

import anyio
from fastapi import HTTPException, Request, status

from .config import get_settings


class FixedWindowLimiter:
    def __init__(self) -> None:
        self._requests: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = anyio.Lock()

    async def __call__(self, request: Request) -> None:
        limit = get_settings().public_demo_requests_per_minute
        if limit <= 0:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Demo paused"
            )
        key = request.client.host if request.client else "unknown"
        cutoff = monotonic() - 60
        async with self._lock:
            timestamps = self._requests[key]
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()
            if len(timestamps) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Public demo rate limit exceeded",
                    headers={"Retry-After": "60"},
                )
            timestamps.append(monotonic())
            if len(self._requests) > 5000:
                self._requests = defaultdict(
                    deque,
                    {client: values for client, values in self._requests.items() if values},
                )


public_demo_rate_limiter = FixedWindowLimiter()
