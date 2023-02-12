#!/usr/bin/env python3
import os
import re
import sys
import json
import urllib.error
import urllib.request
import multiprocessing

SCRIPT_NAME = os.path.basename(os.path.abspath(__file__))
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, '..'))
from yt_dlp.extractor.youtube import YoutubeBaseInfoExtractor


def match_instances(instances):
    '''Return URLs that are not matched by YoutubeBaseInfoExtractor._INVIDIOUS_SITES'''

    res = [re.compile(r) for r in YoutubeBaseInfoExtractor._INVIDIOUS_SITES]
    unmatched_instances = set()

    for instance in instances:
        matched = False
        for r in res:
            if matched:
                break
            if r.match(instance, 0):
                matched = True
                print("- '%s' matches '%s'" % (instance, r.pattern))
        if not matched:
            unmatched_instances.add(instance)

    return unmatched_instances


def match_known_invidious_instances():
    '''Fetch known invidious instances and return unmatched ones'''

    url = 'https://api.invidious.io/instances.json'
    instances = json.load(urllib.request.urlopen(url))
    # the JSON is an array of (instancename, { parameters... }) items
    return match_instances([item[0] for item in instances])


# the Piped docs only list the API URLs, which redirect to the actual site
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


NO_REDIRECT_OPENER = urllib.request.build_opener(NoRedirect)
# this seems to be enough to trick most cloudflared instances:
NO_REDIRECT_OPENER.addheaders = [('User-Agent', 'curl/7.74.0')]


def resolve_piped_instance(api_url):
    '''Return Piped instance for a single API URL'''

    # print('trying', api_url)
    try:
        NO_REDIRECT_OPENER.open(api_url)
    except urllib.error.HTTPError as e:
        if e.getcode() == 403:
            print('skipping', api_url, e, '(might be CloudFlare)')
        elif e.getcode() in [301, 302, 303, 307, 308]:
            if e.headers and e.headers.get:
                instance = e.headers.get('Location')
                # print ("trying", api_url, "resolved to", instance)
                instance = instance.removeprefix('http://')
                instance = instance.removeprefix('https://')
                return instance
        else:
            print('skipping', api_url, e)
    except Exception as e:
        print('skipping', api_url, e)


def match_known_piped_instances():
    '''Fetch known Piped instances and return unmatched ones'''

    url = 'https://raw.githubusercontent.com/wiki/TeamPiped/Piped/Instances.md'
    contents = urllib.request.urlopen(url).read().decode('utf-8')

    # parse second column of Markdown table
    api_urls = set()
    url_re = re.compile(r'^[^|]+\|\s*(?P<url>https?://[^\s|]+)\s*\|')
    for line in contents.split('\n'):
        m = url_re.match(line)
        if m and m.group('url'):
            api_urls.add(m.group('url'))

    instances = set()
    with multiprocessing.Pool() as pool:
        instances = pool.map(resolve_piped_instance, api_urls)

    # filter out Nones and empty strings
    instances = set([x for x in instances if x and len(x)])
    return match_instances(instances)


def print_instances(instances):
    '''Print regex pattern for instances'''
    for instance in instances:
        instance = instance.replace('.', r'\.')
        print(r"        r'(?:www\.)?%s'," % instance)


def main():
    '''Usage:
    {script} <instances...>
    {script}

    With parameters, generate regex patterns for <instances...> which are not yet
    known by yt_dlp.extractor.youtube.YoutubeBaseInfoExtractor._INVIDIOUS_SITES.

    Without parameters, get known Invidious and Piped instances, and generate
    patterns from them.'''

    unmatched_invidious_instances = []
    unmatched_piped_instances = []

    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h', '-?']:
            print(main.__doc__.format(script=SCRIPT_NAME))
            sys.exit(0)
        else:
            unmatched_invidious_instances = match_instances(sys.argv[1:])
    else:
        print('Fetching known Invidious instances...')
        unmatched_invidious_instances = match_known_invidious_instances()
        print('\nFetching and resolving known Piped instances...')
        unmatched_piped_instances = match_known_piped_instances()

    if len(unmatched_invidious_instances) + len(unmatched_piped_instances):
        print('\nThere were unmatched instances!\n'
              'Add the following patterns to _INVIDIOUS_SITES:')
        if len(unmatched_invidious_instances):
            print('\n        # invidious instances:')
            print_instances(unmatched_invidious_instances)
        if len(unmatched_piped_instances):
            print('\n        # piped instances:')
            print_instances(unmatched_piped_instances)
    else:
        print('Found no unmatched instances.')


if __name__ == '__main__':
    main()
