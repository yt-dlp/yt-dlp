with open('bundle.js', 'r', encoding='utf-8') as f:
    content = f.read()

import re

m = re.search(r'XK=w\.memo\(\(\)=>\{', content)
if m:
    start = m.start()
    chunk = content[start:start+25000]
    # search for api calls or videoUrl
    for cm in re.finditer(r'(?:ct\.get|\/api\/|videoUrl)', chunk):
        idx = cm.start()
        print(chunk[max(0, idx-100):min(len(chunk), idx+200)])
        print("="*40)

