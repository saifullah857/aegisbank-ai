"""In-process request metrics (single worker; resets on restart — audit_logs is the durable record)."""
import threading
import time
from collections import deque


class _Metrics:
    def __init__(self):
        self._lock, self.started = threading.Lock(), time.time()
        self.requests = self.errors = 0
        self._lat: deque[float] = deque(maxlen=500)

    def record(self, ms: float, status: int):
        with self._lock:
            self.requests += 1
            self.errors += status >= 500
            self._lat.append(ms)

    def snapshot(self) -> dict:
        with self._lock:
            lat, n, e = sorted(self._lat), self.requests, self.errors
        return {"uptime_seconds": round(time.time() - self.started, 1), "request_count": n,
                "error_rate_percent": round(e / n * 100, 2) if n else 0.0,
                "latency_ms_avg": round(sum(lat) / len(lat), 1) if lat else None,
                "latency_ms_p95": round(lat[max(0, int(len(lat) * 0.95) - 1)], 1) if lat else None}


metrics = _Metrics()
