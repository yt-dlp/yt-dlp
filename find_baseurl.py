with open('bundle.js', 'r', encoding='utf-8') as f:
    s = f.read()
import re
print('appApiHomeEndpoint:', re.findall(r'appApiHomeEndpoint:[^,}]+', s))
print('baseURL:', re.findall(r'baseURL:[^,}]+', s))
print('ct axios:', re.findall(r'ct\s*=\s*axios\.create\([^)]+\)', s))

