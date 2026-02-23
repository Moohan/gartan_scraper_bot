
import time
from api_server import app

def benchmark():
    client = app.test_client()

    # Warm up
    client.get('/')

    start_time = time.time()
    n = 100
    for _ in range(n):
        client.get('/')
    end_time = time.time()

    avg_time = (end_time - start_time) / n
    print(f"Average time for /: {avg_time*1000:.2f}ms")

    start_time = time.time()
    for _ in range(n):
        client.get('/appliances/P22P6/available')
    end_time = time.time()

    avg_time = (end_time - start_time) / n
    print(f"Average time for /appliances/P22P6/available: {avg_time*1000:.2f}ms")

if __name__ == "__main__":
    benchmark()
