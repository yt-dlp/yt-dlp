# Search for nY definition in bundle.js
with open('bundle.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('nY=')
if idx != -1:
    print('Found nY at', idx)
    print(text[idx:idx+1500])

