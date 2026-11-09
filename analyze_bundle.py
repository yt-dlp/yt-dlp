import urllib.request
import re
import json

url = 'https://aryplus.tv/assets/index-CRmzcT3W.js'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
content = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')

# Save bundle locally so we don't redownload every time
with open('bundle.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('Saved bundle.js, size:', len(content))

api_paths = set(re.findall(r'["\'](/api/[^"\']+)["\']', content))
print('API paths found:', len(api_paths))
for p in sorted(api_paths):
    print(' ', p)

