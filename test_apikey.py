import urllib.request
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Origin': 'https://aryplus.tv',
    'Referer': 'https://aryplus.tv/',
    'x-api-key': 'ak_37515186786306625012043079404171'
}

urls = [
    'https://be.aryplus.tv/api/v2/homev2/v2/669f5e353fe1bf91a6a4e273/1',
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
            print('Type:', type(parsed))
            if isinstance(parsed, dict):
                print('Keys:', list(parsed.keys()))
            elif isinstance(parsed, list):
                print('List count:', len(parsed))
            with open('api_success.json', 'w', encoding='utf-8') as f:
                json.dump(parsed, f, indent=2)
            break
    except Exception as e:
        print('Error:', e)

