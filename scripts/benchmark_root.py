import time
import os
import sys
from datetime import datetime

# Set up environment
os.environ["PYTEST_CURRENT_TEST"] = "1" # Prevent config.py from using /app path
sys.path.insert(0, ".")

import api_server
from api_server import app

# Point to benchmark database
api_server.DB_PATH = "benchmark.db"

def benchmark(n=100):
    client = app.test_client()

    # Warm up
    client.get("/")

    start = time.time()
    for _ in range(n):
        client.get("/")
    end = time.time()

    avg = (end - start) / n * 1000
    print(f"Average time for /: {avg:.2f}ms (over {n} requests)")

if __name__ == "__main__":
    benchmark()
