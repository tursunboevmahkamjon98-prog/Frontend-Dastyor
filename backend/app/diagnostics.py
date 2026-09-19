import os
import time

_STARTED_AT = time.monotonic()

_CGROUP_V2 = "/sys/fs/cgroup"
_CGROUP_V1 = "/sys/fs/cgroup/memory"


def _read_text(path: str) -> str | None:
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return None


def _read_int(path: str) -> int | None:
    raw = _read_text(path)
    if raw is None:
        return None
    raw = raw.strip()
    if raw == "max":
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    if value >= 1 << 62:
        return None
    return value


def _mb(value: int | None) -> float | None:
    if value is None:
        return None
    return round(value / (1024 * 1024), 1)


def _cgroup_events() -> dict[str, int]:
    raw = _read_text(f"{_CGROUP_V2}/memory.events")
    if raw is None:
        return {}
    out: dict[str, int] = {}
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("-").isdigit():
            out[parts[0]] = int(parts[1])
    return out


def _process_rss_bytes() -> int | None:
    raw = _read_text("/proc/self/statm")
    if raw is None:
        return None
    fields = raw.split()
    if len(fields) < 2:
        return None
    try:
        return int(fields[1]) * os.sysconf("SC_PAGE_SIZE")
    except (ValueError, OSError):
        return None


def _host_available_bytes() -> int | None:
    raw = _read_text("/proc/meminfo")
    if raw is None:
        return None
    for line in raw.splitlines():
        if line.startswith("MemAvailable:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1]) * 1024
    return None


def memory_report() -> dict:
    events = _cgroup_events()

    current = _read_int(f"{_CGROUP_V2}/memory.current")
    limit = _read_int(f"{_CGROUP_V2}/memory.max")
    peak = _read_int(f"{_CGROUP_V2}/memory.peak")
    oom_kills = events.get("oom_kill")

    if current is None:
        current = _read_int(f"{_CGROUP_V1}/memory.usage_in_bytes")
        limit = _read_int(f"{_CGROUP_V1}/memory.limit_in_bytes")
        peak = _read_int(f"{_CGROUP_V1}/memory.max_usage_in_bytes")
        oom_kills = _read_int(f"{_CGROUP_V1}/memory.failcnt")

    return {
        "uptime_seconds": round(time.monotonic() - _STARTED_AT),
        "process_rss_mb": _mb(_process_rss_bytes()),
        "cgroup_current_mb": _mb(current),
        "cgroup_peak_mb": _mb(peak),
        "cgroup_limit_mb": _mb(limit),
        "host_available_mb": _mb(_host_available_bytes()),
        "oom_kills": oom_kills,
    }
