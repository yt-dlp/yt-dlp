with open('bundle.js', 'r', encoding='utf-8') as f:
    s = f.read()

import re

m = re.search(r'ct\.interceptors\.request\.use\(', s)
if m:
    idx = m.start()
    print(s[idx-100:idx+1500])

