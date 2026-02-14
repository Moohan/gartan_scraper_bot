
import time
from api_server import app

def benchmark():
    client = app.test_client()

    # Warm up
    client.get('/')

    start_time = time.time()
    iterations = 100
    for _ in range(iterations):
        client.get('/')
    end_time = time.time()

    avg_time = (end_time - start_time) / iterations
    print(f"Average time for / route over {iterations} iterations: {avg_time:.4f} seconds")

if __name__ == "__main__":
    benchmark()
