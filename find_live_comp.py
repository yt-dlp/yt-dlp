with open('bundle.js', 'r', encoding='utf-8') as f:
    s = f.read()

import re

for name in ["ZK", "QK", "rY", "mEe"]:
    print(f"=== COMPONENT {name} ===")
    matches = list(re.finditer(rf'[,;\s]{name}\s*=\s*(?:w\.memo\()?\(?', s))
    for m in matches:
        idx = m.start()
        print(s[idx:idx+1500])
        print("="*40)

