import time

from parse_grid import parse_grid_html


def benchmark_parse():
    with open("grid_05-08-2025.html", "r") as f:
        html = f.read()

    start_time = time.time()
    for _ in range(10):
        parse_grid_html(html, "05/08/2025")
    end_time = time.time()
    avg_time = (end_time - start_time) / 10
    print(f"Average time for parse_grid_html: {avg_time:.4f}s")


if __name__ == "__main__":
    benchmark_parse()
