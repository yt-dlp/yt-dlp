with open('bundle.js', 'r', encoding='utf-8') as f:
    s = f.read()

import re

# Search for shorts API
for m in re.finditer(r'/shorts', s):
    idx = m.start()
    print("SHORTS:", s[max(0, idx-100):min(len(s), idx+200)])
    print("="*40)

# Search for live / watch component logic
for m in re.finditer(r'/(?:live|watch)/v[12]', s):
    idx = m.start()
    print("LIVE/WATCH:", s[max(0, idx-100):min(len(s), idx+200)])
    print("="*40)

