with open('bundle.js', 'r', encoding='utf-8') as f:
    s = f.read()

import re

m = re.search(r'ZK=w\.memo\(\(\)=>\{', s)
if m:
    idx = m.start()
    print(s[idx:idx+4000])

