from __future__ import annotations

from dataclasses import dataclass
import sys
import time
from urllib import error, request


ROUTES = (
    "/",
    "/topic",
    "/search",
    "/sources",
    "/support",
    "/studio",
    "/chronology",
)


@dataclass(frozen=True)
class CheckResult:
    route: str
    url: str
    status_code: int | None
    elapsed_ms: int
    error_message: str = ""

    @property
    def ok(self) -> bool:
        return self.status_code is not None and 200 <= self.status_code < 400 and not self.error_message


def _normalize_base_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ValueError("base URL is required")
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value.rstrip("/")


def _check_url(url: str, route: str, *, timeout_seconds: float = 15.0) -> CheckResult:
    started = time.perf_counter()
    req = request.Request(url, headers={"User-Agent": "datosenorden-healthcheck/1.0"})
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            status_code = response.status
            error_message = ""
    except error.HTTPError as exc:
        status_code = exc.code
        error_message = str(exc)
    except error.URLError as exc:
        status_code = None
        error_message = str(exc.reason)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return CheckResult(route=route, url=url, status_code=status_code, elapsed_ms=elapsed_ms, error_message=error_message)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python3 scripts/healthcheck_public.py https://beta.datosenorden.cl")
        return 2

    try:
        base_url = _normalize_base_url(argv[1])
    except ValueError as exc:
        print(f"error: {exc}")
        return 2

    print(f"healthcheck_public: base_url={base_url}")
    results: list[CheckResult] = []
    for route in ROUTES:
        url = f"{base_url}{route}"
        result = _check_url(url, route)
        results.append(result)
        status_text = str(result.status_code) if result.status_code is not None else "ERROR"
        detail = result.error_message or "ok"
        label = "ok" if result.ok else "FAIL"
        print(f"  {label} {route} status={status_text} time_ms={result.elapsed_ms} detail={detail}")

    ok_count = sum(1 for result in results if result.ok)
    fail_count = len(results) - ok_count
    print(f"summary: ok={ok_count} fail={fail_count} total={len(results)}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
