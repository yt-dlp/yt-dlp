import json

with open('api_success.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

items = []

def extract_items(obj):
    if isinstance(obj, dict):
        if '_id' in obj and 'title' in obj:
            items.append(obj)
        for v in obj.values():
            extract_items(v)
    elif isinstance(obj, list):
        for elem in obj:
            extract_items(elem)

extract_items(data)
print(f"Total items found: {len(items)}")

for it in items[:10]:
    print(f"ID: {it.get('_id')}, Title: {it.get('title')}, Type: {it.get('seriesType')}, DRM: {it.get('drmEnabled')}")

