"""
Benchmark Latensi Middleware — 100 request campuran (50 normal + 50 attack).
Mengukur end-to-end latency: client → Flask middleware → Inference API → response.

Usage: python scripts/bench_middleware.py
Output: data/bench_latency_100.json + stdout table
"""
import json
import os
import sys
import time
import statistics

import requests

BASE_URL = "http://127.0.0.1:5000"

# ──────────────────────────────────────────────
# Request definitions
# ──────────────────────────────────────────────
NORMAL_REQUESTS = [
    # 17x GET /home
    *[{"method": "GET", "url": f"{BASE_URL}/home"} for _ in range(17)],
    # 17x GET /search?q=hello (benign query)
    *[{"method": "GET", "url": f"{BASE_URL}/search?q=hello"} for _ in range(17)],
    # 16x POST /login normal form
    *[{
        "method": "POST",
        "url": f"{BASE_URL}/login",
        "data": {"username": f"user{i}", "password": "pass123"},
    } for i in range(16)],
]

ATTACK_REQUESTS = [
    # 10x SQL Injection via search
    *[{"method": "GET", "url": f"{BASE_URL}/search?q=test'+OR+1%3D1--"} for _ in range(10)],
    # 10x SQL Injection via login form
    *[{
        "method": "POST",
        "url": f"{BASE_URL}/login",
        "data": {"username": "admin' UNION SELECT * FROM users--", "password": "x"},
    } for _ in range(10)],
    # 10x XSS via search
    *[{"method": "GET", "url": f"{BASE_URL}/search?q=<script>alert(1)</script>"} for _ in range(10)],
    # 10x Path traversal
    *[{"method": "GET", "url": f"{BASE_URL}/search?q=../../etc/passwd"} for _ in range(10)],
    # 10x Command injection
    *[{"method": "GET", "url": f"{BASE_URL}/search?q=;cat+/etc/passwd"} for _ in range(10)],
]

ALL_REQUESTS = NORMAL_REQUESTS + ATTACK_REQUESTS


def measure_latency(req: dict) -> float:
    """Send one request and return latency in ms."""
    method = req["method"]
    url = req["url"]
    data = req.get("data")

    start = time.perf_counter()
    if method == "GET":
        resp = requests.get(url, timeout=5)
    elif method == "POST":
        resp = requests.post(url, data=data, timeout=5)
    else:
        raise ValueError(f"Unknown method: {method}")
    elapsed = (time.perf_counter() - start) * 1000  # ms
    return elapsed


def run_benchmark(run_name: str = "bench_latency_100") -> dict:
    """Run all requests and compute stats."""
    latencies = []
    for req in ALL_REQUESTS:
        lat = measure_latency(req)
        latencies.append(lat)

    latencies_sorted = sorted(latencies)
    n = len(latencies_sorted)

    def percentile(data, pct):
        k = (pct / 100) * (len(data) - 1)
        f = int(k)
        c = f + 1 if f + 1 < len(data) else f
        d = k - f
        return data[f] + d * (data[c] - data[f])

    result = {
        "run_name": run_name,
        "total_requests": n,
        "normal_count": len(NORMAL_REQUESTS),
        "attack_count": len(ATTACK_REQUESTS),
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2),
        "mean_ms": round(statistics.mean(latencies), 2),
        "p50_ms": round(percentile(latencies_sorted, 50), 2),
        "p95_ms": round(percentile(latencies_sorted, 95), 2),
        "p99_ms": round(percentile(latencies_sorted, 99), 2),
        "all_under_100ms": all(l < 100 for l in latencies),
    }
    return result


def main():
    data_dir = os.path.join(os.path.dirname(__file__), os.pardir, "data")
    os.makedirs(data_dir, exist_ok=True)

    run_label = sys.argv[1] if len(sys.argv) > 1 else "bench_latency_100"
    result = run_benchmark(run_label)
    out_path = os.path.join(data_dir, f"{run_label}.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n{'='*50}")
    print(f"  Benchmark: {run_label}")
    print(f"{'='*50}")
    print(f"  Total requests : {result['total_requests']}")
    print(f"  Normal / Attack: {result['normal_count']} / {result['attack_count']}")
    print(f"  Min             : {result['min_ms']:.2f} ms")
    print(f"  Max             : {result['max_ms']:.2f} ms")
    print(f"  Mean            : {result['mean_ms']:.2f} ms")
    print(f"  P50 (median)    : {result['p50_ms']:.2f} ms")
    print(f"  P95             : {result['p95_ms']:.2f} ms")
    print(f"  P99             : {result['p99_ms']:.2f} ms")
    print(f"  All < 100ms     : {'YES ✅' if result['all_under_100ms'] else 'NO ❌'}")
    print(f"{'='*50}")
    print(f"  Saved to: {os.path.abspath(out_path)}")

    return result


if __name__ == "__main__":
    main()
