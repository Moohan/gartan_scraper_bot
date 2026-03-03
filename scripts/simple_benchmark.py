import statistics
import time

import requests


def benchmark(url, iterations=100):
    latencies = []
    for _ in range(iterations):
        start = time.perf_counter()
        try:
            r = requests.get(url)
            r.raise_for_status()
            latencies.append(time.perf_counter() - start)
        except Exception as e:
            print(f"Error: {e}")

    if latencies:
        avg = statistics.mean(latencies) * 1000
        std = statistics.stdev(latencies) * 1000
        print(f"URL: {url}")
        print(f"Average: {avg:.2f}ms")
        print(f"StdDev: {std:.2f}ms")
        print(f"Min: {min(latencies)*1000:.2f}ms")
        print(f"Max: {max(latencies)*1000:.2f}ms")


if __name__ == "__main__":
    # We need the server running.
    # For now, this is just a template.
    pass
