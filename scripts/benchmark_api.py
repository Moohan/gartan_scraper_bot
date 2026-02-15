import time

from api_server import app


def benchmark():
    client = app.test_client()

    # Warm up
    client.get("/")

    start = time.time()
    iterations = 50
    for _ in range(iterations):
        client.get("/")
    end = time.time()

    avg_time = (end - start) / iterations * 1000
    print(f"Average time for / route: {avg_time:.2f}ms")


if __name__ == "__main__":
    benchmark()
