with open('bundle.js', 'r', encoding='utf-8') as f:
    content = f.read()

import re

def search_func(name):
    print(f"=== SEARCH FOR {name} ===")
    matches = list(re.finditer(rf'(?:function\s+{name}\b|const\s+{name}\s*=\s*(?:w\.memo\()?\(?|\b{name}\s*=\s*function|\b{name}\s*=\s*\()', content))
    for m in matches:
        start = max(0, m.start() - 50)
        end = min(len(content), m.end() + 1500)
        print(content[start:end])
        print("-" * 50)

search_func("XK")
search_func("iY")
search_func("xEe")

