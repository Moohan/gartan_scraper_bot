import os
import time

from api_server import DB_PATH, app


def benchmark():
    print(f"Using DB_PATH: {DB_PATH}")
    print(f"DB exists: {os.path.exists(DB_PATH)}")

    client = app.test_client()

    # Warm up
    resp = client.get("/")
    print(f"Warm up status: {resp.status_code}")
    if resp.status_code != 200:
        print(resp.json)

    start = time.time()
    for _ in range(100):
        client.get("/")
    end = time.time()

    avg_latency = (end - start) / 100 * 1000
    print(f"Average latency for /: {avg_latency:.2f}ms")


if __name__ == "__main__":
    benchmark()
