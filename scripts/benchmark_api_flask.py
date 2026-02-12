import statistics
import time

from api_server import app


def benchmark_root(n=50):
    client = app.test_client()
    latencies = []

    # Warm up
    client.get("/")

    for i in range(n):
        start = time.perf_counter()
        response = client.get("/")
        end = time.perf_counter()
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            continue
        latencies.append((end - start) * 1000)

    print(f"Benchmark results for '/' endpoint ({n} requests):")
    print(f"  Average: {statistics.mean(latencies):.2f} ms")
    print(f"  Median:  {statistics.median(latencies):.2f} ms")
    print(f"  Min:     {min(latencies):.2f} ms")
    print(f"  Max:     {max(latencies):.2f} ms")
    print(f"  StdDev:  {statistics.stdev(latencies):.2f} ms")


if __name__ == "__main__":
    benchmark_root()
