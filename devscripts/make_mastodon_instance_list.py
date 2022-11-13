# coding: utf-8
from __future__ import unicode_literals

import sys
import os
import re
import itertools
sys.path[:0] = ['.', 'devscripts']

from scraper_helper import ie, sanitize_hostname, traverse_sanitize
from yt_dlp.utils import ExtractorError, parse_qs

script_id = 'mastodon'
results = set()

# Mastodon

instance_social_api_key = os.environ.get('INSTANCE_SOCIAL_API_SECRET')
if instance_social_api_key:
    min_id = None
    while True:
        url = 'https://instances.social/api/1.0/instances/list'
        if min_id:
            url = f'{url}?min_id={min_id}'
        data = ie._download_json(
            url, script_id, note=f'Paging {min_id}, len(results)={len(results)}',
            headers={'Authorization': f'Bearer {instance_social_api_key}'})
        results.update(traverse_sanitize(data, ('instances', ..., 'name')))
        min_id = data['pagination'].get('next_id')
        if not min_id:
            break
else:
    ie.report_warning('instances.social fetching is disabled!!!')

joinmastodon_categories = [
    'general', 'regional', 'art', 'music',
    'journalism', 'activism', 'lgbt', 'games',
    'tech', 'academia', 'adult', 'humor',
    'furry', 'food'
]
for category in joinmastodon_categories:
    url = f'https://api.joinmastodon.org/servers?category={category}'
    data = ie._download_json(
        url, script_id, note=f'Category {category}, len(results)={len(results)}')
    for instance in data:
        results.add(sanitize_hostname(instance['domain']))

if True:
    try:
        url = 'https://the-federation.info/graphql?query=query%20Platform(%24name%3A%20String!)%20%7B%0A%20%20platforms(name%3A%20%24name)%20%7B%0A%20%20%20%20name%0A%20%20%20%20code%0A%20%20%20%20displayName%0A%20%20%20%20description%0A%20%20%20%20tagline%0A%20%20%20%20website%0A%20%20%20%20icon%0A%20%20%20%20__typename%0A%20%20%7D%0A%20%20nodes(platform%3A%20%24name)%20%7B%0A%20%20%20%20id%0A%20%20%20%20name%0A%20%20%20%20version%0A%20%20%20%20openSignups%0A%20%20%20%20host%0A%20%20%20%20platform%20%7B%0A%20%20%20%20%20%20name%0A%20%20%20%20%20%20icon%0A%20%20%20%20%20%20__typename%0A%20%20%20%20%7D%0A%20%20%20%20countryCode%0A%20%20%20%20countryFlag%0A%20%20%20%20countryName%0A%20%20%20%20services%20%7B%0A%20%20%20%20%20%20name%0A%20%20%20%20%20%20__typename%0A%20%20%20%20%7D%0A%20%20%20%20__typename%0A%20%20%7D%0A%20%20statsGlobalToday(platform%3A%20%24name)%20%7B%0A%20%20%20%20usersTotal%0A%20%20%20%20usersHalfYear%0A%20%20%20%20usersMonthly%0A%20%20%20%20localPosts%0A%20%20%20%20localComments%0A%20%20%20%20__typename%0A%20%20%7D%0A%20%20statsNodes(platform%3A%20%24name)%20%7B%0A%20%20%20%20node%20%7B%0A%20%20%20%20%20%20id%0A%20%20%20%20%20%20__typename%0A%20%20%20%20%7D%0A%20%20%20%20usersTotal%0A%20%20%20%20usersHalfYear%0A%20%20%20%20usersMonthly%0A%20%20%20%20localPosts%0A%20%20%20%20localComments%0A%20%20%20%20__typename%0A%20%20%7D%0A%7D%0A&operationName=Platform&variables=%7B%22name%22%3A%22mastodon%22%7D'
        data = ie._download_json(
            url, script_id, note=f'Scraping https://the-federation.info/mastodon, len(results)={len(results)}',
            headers={
                'content-type': 'application/json, application/graphql',
                'accept': 'application/json, application/graphql',
            })
        results.update(traverse_sanitize(data, ('data', 'nodes', ..., 'host')))
    except KeyboardInterrupt:
        raise
    except BaseException as ex:
        ie.report_warning(ex)

if True:
    try:
        url = 'https://mastodon.fediverse.observer/tabledata.php?software=mastodon'
        data = ie._download_webpage(
            url, script_id, note=f'Scraping https://mastodon.fediverse.observer, len(results)={len(results)}')
        for instance in re.finditer(r'href="/go\.php\?domain=([a-z0-9\.-]+)">\1</a>', data):
            results.add(sanitize_hostname(instance.group(1)))
    except KeyboardInterrupt:
        raise
    except BaseException as ex:
        ie.report_warning(ex)

for i in itertools.count(1):
    try:
        url = 'https://fedidb.org/network?s=mastodon'
        data, urlh = ie._download_webpage_handle(
            url, script_id, note=f'Scraping https://fedidb.org/network?s=mastodon (Page {i}), len(results)={len(results)}',
            query={'page': str(i)})
        if parse_qs(urlh.geturl())['page'][0] != str(i):
            break
        matches = re.findall(r'(?s)href="/network/instance\?domain=([a-z0-9\.-]+)">\s*\1\s*</a>', data)
        if not matches:
            break
        results.update(sanitize_hostname(instance) for instance in matches)
    except KeyboardInterrupt:
        raise
    except BaseException as ex:
        ie.report_warning(ex)
        break

# Gab Social
ie.to_screen(f'Adding Gab Social to the list, len(results)={len(results)}')
results.add('gab.com')

# Truth Social
ie.to_screen(f'Adding Truth Social to the list, len(results)={len(results)}')
results.add('truthsocial.com')

# Pleroma
if True:
    try:
        url = 'https://pleroma.social/'
        webpage = ie._download_webpage(
            url, script_id, note=f'Scraping https://pleroma.social/, len(results)={len(results)}')
        for mobj in re.finditer(r'href="https?://([^/]+)/?">\1</a>', webpage):
            results.add(mobj.group(1))
    except KeyboardInterrupt:
        raise
    except BaseException as ex:
        ie.report_warning(ex)

if True:
    try:
        url = 'https://the-federation.info/graphql?query=query%20Platform(%24name%3A%20String!)%20%7B%0A%20%20platforms(name%3A%20%24name)%20%7B%0A%20%20%20%20name%0A%20%20%20%20code%0A%20%20%20%20displayName%0A%20%20%20%20description%0A%20%20%20%20tagline%0A%20%20%20%20website%0A%20%20%20%20icon%0A%20%20%20%20__typename%0A%20%20%7D%0A%20%20nodes(platform%3A%20%24name)%20%7B%0A%20%20%20%20id%0A%20%20%20%20name%0A%20%20%20%20version%0A%20%20%20%20openSignups%0A%20%20%20%20host%0A%20%20%20%20platform%20%7B%0A%20%20%20%20%20%20name%0A%20%20%20%20%20%20icon%0A%20%20%20%20%20%20__typename%0A%20%20%20%20%7D%0A%20%20%20%20countryCode%0A%20%20%20%20countryFlag%0A%20%20%20%20countryName%0A%20%20%20%20services%20%7B%0A%20%20%20%20%20%20name%0A%20%20%20%20%20%20__typename%0A%20%20%20%20%7D%0A%20%20%20%20__typename%0A%20%20%7D%0A%20%20statsGlobalToday(platform%3A%20%24name)%20%7B%0A%20%20%20%20usersTotal%0A%20%20%20%20usersHalfYear%0A%20%20%20%20usersMonthly%0A%20%20%20%20localPosts%0A%20%20%20%20localComments%0A%20%20%20%20__typename%0A%20%20%7D%0A%20%20statsNodes(platform%3A%20%24name)%20%7B%0A%20%20%20%20node%20%7B%0A%20%20%20%20%20%20id%0A%20%20%20%20%20%20__typename%0A%20%20%20%20%7D%0A%20%20%20%20usersTotal%0A%20%20%20%20usersHalfYear%0A%20%20%20%20usersMonthly%0A%20%20%20%20localPosts%0A%20%20%20%20localComments%0A%20%20%20%20__typename%0A%20%20%7D%0A%7D%0A&operationName=Platform&variables=%7B%22name%22%3A%22pleroma%22%7D'
        data = ie._download_json(
            url, script_id, note=f'Scraping https://the-federation.info/pleroma, len(results)={len(results)}',
            headers={
                'content-type': 'application/json, application/graphql',
                'accept': 'application/json, application/graphql',
            })
        results.update(traverse_sanitize(data, ('data', 'nodes', ..., 'host')))
    except KeyboardInterrupt:
        raise
    except BaseException as ex:
        ie.report_warning(ex)

if True:
    try:
        url = 'https://pleroma.fediverse.observer/tabledata.php?software=pleroma'
        data = ie._download_webpage(
            url, script_id, note=f'Scraping https://pleroma.fediverse.observer, len(results)={len(results)}')
        for instance in re.finditer(r'href="/go\.php\?domain=([a-z0-9\.-]+)">\1</a>', data):
            results.add(sanitize_hostname(instance.group(1)))
    except KeyboardInterrupt:
        raise
    except BaseException as ex:
        ie.report_warning(ex)

for i in itertools.count(1):
    try:
        url = 'https://fedidb.org/network?s=pleroma'
        data, urlh = ie._download_webpage_handle(
            url, script_id, note=f'Scraping https://fedidb.org/network?s=pleroma (Page {i}), len(results)={len(results)}',
            query={'page': str(i)})
        if parse_qs(urlh.geturl())['page'][0] != str(i):
            break
        matches = re.findall(r'(?s)href="/network/instance\?domain=([a-z0-9\.-]+)">\s*\1\s*</a>', data)
        if not matches:
            break
        results.update(sanitize_hostname(instance) for instance in matches)
    except KeyboardInterrupt:
        raise
    except BaseException as ex:
        ie.report_warning(ex)
        break

ie.to_screen(f'{script_id}: len(results)={len(results)}')

if not results:
    raise ExtractorError('no instances found')

results = {x.encode('idna').decode('utf8') for x in results}
ie.to_screen(f'{script_id}: converted domain names to punycode, len(results)={len(results)}')

results = {x for x in results if '.' in x}
ie.to_screen(f'{script_id}: excluded domain names without dot, len(results)={len(results)}')

results = {x for x in results if not (x.endswith('.ngrok.io') or x.endswith('.localhost.run') or x.endswith('.serveo.net'))}
ie.to_screen(f'{script_id}: excluded temporary domain names, len(results)={len(results)}')

# for it in list(results):
#     try:
#         if not socket.getaddrinfo(it, None):
#             raise ValueError()
#     except BaseException:
#         results.remove(it)

# ie.to_screen(f'{script_id}: removed unavailable domains, len(results)={len(results)}')

lf = '\n'
pycode = f'''# coding: utf-8
# AUTOMATICALLY GENERATED FILE. DO NOT EDIT.
# Generated by ./devscripts/make_mastodon_instance_list.py
from __future__ import unicode_literals

instances = {{
    # list of instances here
{lf.join(f'    "{r}",' for r in sorted(results))}
}}

__all__ = ['instances']
'''

with open('./yt_dlp/extractor/mastodon/instances.py', 'w') as w:
    w.write(pycode)
