from hashlib import sha256
import itertools
import json
import re
import time

from .ffmpeg import FFmpegPostProcessor
from ..compat import compat_urllib_parse_urlencode, compat_HTTPError
from ..utils import PostProcessingError, network_exceptions, sanitized_Request


class SponsorBlockPP(FFmpegPostProcessor):
    # https://wiki.sponsor.ajay.app/w/Types
    EXTRACTORS = {
        'Youtube': 'YouTube',
    }
    POI_CATEGORIES = {
        'poi_highlight': 'Highlight',
    }
    CATEGORIES = {
        'sponsor': 'Sponsor',
        'intro': 'Intermission/Intro Animation',
        'outro': 'Endcards/Credits',
        'selfpromo': 'Unpaid/Self Promotion',
        'preview': 'Preview/Recap',
        'filler': 'Filler Tangent',
        'interaction': 'Interaction Reminder',
        'music_offtopic': 'Non-Music Section',
        **POI_CATEGORIES,
    }

    def __init__(self, downloader, categories=None, api='https://sponsor.ajay.app'):
        FFmpegPostProcessor.__init__(self, downloader)
        self._categories = tuple(categories or self.CATEGORIES.keys())
        self._API_URL = api if re.match('^https?://', api) else 'https://' + api

    def run(self, info):
        extractor = info['extractor_key']
        if extractor not in self.EXTRACTORS:
            self.to_screen(f'SponsorBlock is not supported for {extractor}')
            return [], info

        self.to_screen('Fetching SponsorBlock segments')
        info['sponsorblock_chapters'] = self._get_sponsor_chapters(info, info['duration'])
        return [], info

    def _get_sponsor_chapters(self, info, duration):
        segments = self._get_sponsor_segments(info['id'], self.EXTRACTORS[info['extractor_key']])

        def duration_filter(s):
            start_end = s['segment']
            # Ignore milliseconds difference at the start.
            if start_end[0] <= 1:
                start_end[0] = 0
            # Make POI chapters 1 sec so that we can properly mark them
            if s['category'] in self.POI_CATEGORIES.keys():
                start_end[1] += 1
            # Ignore milliseconds difference at the end.
            # Never allow the segment to exceed the video.
            if duration and duration - start_end[1] <= 1:
                start_end[1] = duration
            # SponsorBlock duration may be absent or it may deviate from the real one.
            return s['videoDuration'] == 0 or not duration or abs(duration - s['videoDuration']) <= 1

        duration_match = [s for s in segments if duration_filter(s)]
        if len(duration_match) != len(segments):
            self.report_warning('Some SponsorBlock segments are from a video of different duration, maybe from an old version of this video')

        def to_chapter(s):
            (start, end), cat = s['segment'], s['category']
            return {
                'start_time': start,
                'end_time': end,
                'category': cat,
                'title': self.CATEGORIES[cat],
                '_categories': [(cat, start, end)]
            }

        sponsor_chapters = [to_chapter(s) for s in duration_match]
        if not sponsor_chapters:
            self.to_screen('No segments were found in the SponsorBlock database')
        else:
            self.to_screen(f'Found {len(sponsor_chapters)} segments in the SponsorBlock database')
        return sponsor_chapters

    def _get_sponsor_segments(self, video_id, service):
        hash = sha256(video_id.encode('ascii')).hexdigest()
        # SponsorBlock API recommends using first 4 hash characters.
        url = f'{self._API_URL}/api/skipSegments/{hash[:4]}?' + compat_urllib_parse_urlencode({
            'service': service,
            'categories': json.dumps(self._categories),
        })
        self.write_debug(f'SponsorBlock query: {url}')
        for d in self._get_json(url):
            if d['videoID'] == video_id:
                return d['segments']
        return []

    def _get_json(self, url):
        # While this is not an extractor, it behaves similar to one and
        # so obey extractor_retries and sleep_interval_requests
        max_retries = self.get_param('extractor_retries', 3)
        sleep_interval = self.get_param('sleep_interval_requests') or 0
        for retries in itertools.count():
            try:
                rsp = self._downloader.urlopen(sanitized_Request(url))
                return json.loads(rsp.read().decode(rsp.info().get_param('charset') or 'utf-8'))
            except network_exceptions as e:
                if isinstance(e, compat_HTTPError) and e.code == 404:
                    return []
                if retries < max_retries:
                    self.report_warning(f'{e}. Retrying...')
                    if sleep_interval > 0:
                        self.to_screen(f'Sleeping {sleep_interval} seconds ...')
                        time.sleep(sleep_interval)
                    continue
                raise PostProcessingError(f'Unable to communicate with SponsorBlock API: {e}')
