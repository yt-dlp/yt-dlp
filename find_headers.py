with open('bundle.js', 'r', encoding='utf-8') as f:
    s = f.read()

import re

# Look for headers in axios configuration or interceptors
print("--- Search for headers: { ... } or interceptors ---")
for m in re.finditer(r'(?:headers\s*:\s*\{|interceptors\.request\.use\()', s):
    idx = m.start()
    print(s[max(0, idx-50):min(len(s), idx+400)])
    print("="*50)

