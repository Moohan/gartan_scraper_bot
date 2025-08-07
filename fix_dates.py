#!/usr/bin/env python3
"""Fix date formats in test files"""

import re

files = ['tests/test_db_store_expanded.py']

for file in files:
    with open(file, 'r') as f:
        content = f.read()
    
    # Replace YYYY-MM-DD HHMM format with DD/MM/YYYY HHMM format
    content = re.sub(r'"(\d{4})-(\d{2})-(\d{2}) (\d{4})"', r'"\3/\2/\1 \4"', content)
    
    with open(file, 'w') as f:
        f.write(content)

print('Date formats fixed')
