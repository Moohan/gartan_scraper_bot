
import time
from api_server import app
import os

def benchmark():
    client = app.test_client()

    # Warm up
    client.get('/')

    iterations = 50
    start = time.time()
    for _ in range(iterations):
        client.get('/')
    end = time.time()

    avg = (end - start) / iterations * 1000
    print(f"Average response time for '/': {avg:.2f}ms")

if __name__ == "__main__":
    benchmark()
