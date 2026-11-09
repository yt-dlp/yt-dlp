with open('bundle.js', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Find occurrences of '/video/v'
for match in re.finditer(r'/video/v[12]', content):
    start = max(0, match.start() - 200)
    end = min(len(content), match.end() + 500)
    print("--- MATCH AT", match.start(), "---")
    print(content[start:end])
    print()

