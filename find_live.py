import json

with open('api_success.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

live_items = []
def find_live(obj):
    if isinstance(obj, dict):
        if obj.get('isLive') or obj.get('seriesType') in ['live', 'live-event']:
            live_items.append(obj)
        for v in obj.values():
            find_live(v)
    elif isinstance(obj, list):
        for elem in obj:
            find_live(elem)

find_live(data)
print(f"Total live items found: {len(live_items)}")
for item in live_items[:5]:
    print(item.get('_id'), item.get('title'), item.get('seriesType'), item.get('isLive'), item.get('seiresCDNWebKey'), item.get('seiresCDNWebLink'))

