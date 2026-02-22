import time
from api_server import app

def benchmark_root():
    client = app.test_client()
    latencies = []

    # Warm up
    client.get("/")

    for _ in range(20):
        start = time.time()
        res = client.get("/")
        end = time.time()
        if res.status_code == 200:
            latencies.append((end - start) * 1000)

    if latencies:
        avg = sum(latencies) / len(latencies)
        print(f"Average latency for /: {avg:.2f}ms (min: {min(latencies):.2f}ms, max: {max(latencies):.2f}ms)")
    else:
        print("Failed to get successful responses")

if __name__ == "__main__":
    benchmark_root()
