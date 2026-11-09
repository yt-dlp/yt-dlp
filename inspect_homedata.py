import json

with open('api_success.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

homeData = data['home']['homeData']
print(f"Total sections in homeData: {len(homeData)}")

for i, section in enumerate(homeData):
    sec_title = section.get('title')
    sec_type = section.get('seriesLayout') or section.get('type')
    series = section.get('series') or []
    print(f"Section {i}: title='{sec_title}', series_count={len(series)}")
    for s in series[:2]:
        print(f"   _id: {s.get('_id')}, title: {s.get('title')}, type: {s.get('seriesType')}, drm: {s.get('drmEnabled')}")

