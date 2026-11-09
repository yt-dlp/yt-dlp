with open('bundle.js', 'r', encoding='utf-8') as f:
    content = f.read()

import re

m = re.search(r'XK=w\.memo\(\(\)=>\{', content)
if m:
    start = m.start()
    # print next 4000 characters
    print(content[start:start+4000])

