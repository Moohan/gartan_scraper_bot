# Demonstration: Infinite cache behaviour (moved from root test_infinite_cache.py)
import os
import tempfile

from config import config
from gartan_fetch import _is_cache_valid


def main():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as temp_file:
        temp_file.write('<html>Test cache data</html>')
        cache_file = temp_file.name
    try:
        for day_offset in [-7,-1,0,1,7]:
            cache_minutes = config.get_cache_minutes(day_offset)
            valid = _is_cache_valid(cache_file, cache_minutes)
            print(day_offset, cache_minutes, valid)
    finally:
        os.unlink(cache_file)

if __name__ == '__main__':
    main()
