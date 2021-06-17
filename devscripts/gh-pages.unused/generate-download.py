#!/usr/bin/env python3
from __future__ import unicode_literals

import json

versions_info = json.load(open('update/versions.json'))
version = versions_info['latest']
version_dict = versions_info['versions'][version]

# Read template page
with open('download.html.in', 'r', encoding='utf-8') as tmplf:
    template = tmplf.read()

template = template.replace('@PROGRAM_VERSION@', version)
template = template.replace('@PROGRAM_URL@', version_dict['bin'][0])
template = template.replace('@PROGRAM_SHA256SUM@', version_dict['bin'][1])
template = template.replace('@EXE_URL@', version_dict['exe'][0])
template = template.replace('@EXE_SHA256SUM@', version_dict['exe'][1])
template = template.replace('@TAR_URL@', version_dict['tar'][0])
template = template.replace('@TAR_SHA256SUM@', version_dict['tar'][1])
with open('download.html', 'w', encoding='utf-8') as dlf:
    dlf.write(template)
