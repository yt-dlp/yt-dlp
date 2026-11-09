import re

with open('bundle.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Search for route paths
routes = set(re.findall(r'path:\s*["\']([^"\']+)["\']', content))
print('Routes found:')
for r in sorted(routes):
    print(' ', r)

# Also search for "https://aryplus.tv/" links or path definitions
route_elements = set(re.findall(r'path:\s*`([^`]+)`', content))
for r in sorted(route_elements):
    print(' `', r)

