import json

with open('api_success.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

home = data.get('home', [])
print(f"Total sections in home: {len(home)}")

for i, section in enumerate(home[:10]):
    sec_title = section.get('title') or section.get('sectionTitle') or section.get('name')
    sec_type = section.get('type') or section.get('sectionType')
    items = section.get('items') or section.get('data') or section.get('series') or []
    print(f"Section {i}: title={sec_title}, type={sec_type}, items_count={len(items)}")
    if items and i < 5:
        first_item = items[0]
        print(f"   Sample item keys: {list(first_item.keys())}")
        print(f"   _id: {first_item.get('_id')}, title: {first_item.get('title')}, seriesType: {first_item.get('seriesType')}")

