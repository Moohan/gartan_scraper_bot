
import time
import os
from api_server import app, get_db
import api_server

def benchmark_root(db_path, iterations=100):
    # Monkeypatch DB_PATH in api_server
    api_server.DB_PATH = db_path

    client = app.test_client()

    # Warm up
    client.get('/')

    start_time = time.perf_counter()
    for _ in range(iterations):
        client.get('/')
    end_time = time.perf_counter()

    avg_time = (end_time - start_time) / iterations
    print(f"Average time for / over {iterations} iterations: {avg_time*1000:.2f}ms")
    return avg_time

if __name__ == "__main__":
    db_path = "data/benchmark.db"
    if not os.path.exists(db_path):
        print("Run setup_benchmark.py first")
    else:
        benchmark_root(db_path)
