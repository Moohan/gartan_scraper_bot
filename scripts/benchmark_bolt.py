import os
import sys
import time

# Add the root directory to the python path so we can import api_server
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import api_server
from api_server import app


def benchmark_root(iterations=100):
    # Override DB_PATH in api_server
    api_server.DB_PATH = "benchmark.db"

    app.config["TESTING"] = True
    client = app.test_client()

    # Warm up
    resp = client.get("/")
    if resp.status_code != 200:
        print(f"Error during warm up: {resp.status_code}")
        print(resp.data.decode())
        return

    start_time = time.time()
    for _ in range(iterations):
        client.get("/")
    end_time = time.time()

    avg_time = (end_time - start_time) / iterations * 1000
    print(f"Average time for /: {avg_time:.2f}ms")
    return avg_time


if __name__ == "__main__":
    benchmark_root()
