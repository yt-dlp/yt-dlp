import urllib.request
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Origin': 'https://aryplus.tv',
    'Referer': 'https://aryplus.tv/'
}

# Try fetching home data
urls = [
    'https://be.aryplus.tv/api/v2/homev2/v2/669f5e353fe1bf91a6a4e273/1',
    'https://be.aryplus.tv/api/v2/homev2/v2/669f5e353fe1bf91a6a4e273',
    'https://be.aryplus.tv/api/v2/search?query=a'
]

for url in urls:
    print('Testing URL:', url)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            print('Success! Status:', resp.status, 'Length:', len(data))
            parsed = json.loads(data.decode('utf-8'))
            print('Keys:', list(parsed.keys()) if isinstance(parsed, dict) else f'List of {len(parsed)}')
            # Save sample to file
            with open('home_sample.json', 'w', encoding='utf-8') as f:
                json.dump(parsed, f, indent=2)
            break
    except Exception as e:
        print('Error:', e)

