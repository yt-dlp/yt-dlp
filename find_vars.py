with open('bundle.js', 'r', encoding='utf-8') as f:
    content = f.read()

import re

for name in ["XK", "xEe"]:
    print(f"=== OCCURRENCES OF {name} ===")
    matches = list(re.finditer(rf'[,;\s]{name}\s*=', content))
    for m in matches:
        start = max(0, m.start() - 50)
        end = min(len(content), m.end() + 1000)
        print(content[start:end])
        print("="*40)

