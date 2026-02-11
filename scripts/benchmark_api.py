import time

from api_server import app


def benchmark_root():
    client = app.test_client()
    start_time = time.time()
    for _ in range(10):
        response = client.get("/")
        assert response.status_code == 200
    end_time = time.time()
    avg_time = (end_time - start_time) / 10
    print(f"Average time for /: {avg_time:.4f}s")


if __name__ == "__main__":
    benchmark_root()
