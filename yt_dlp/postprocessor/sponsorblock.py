import hashlib
import json
import re
import urllib.parse

from .ffmpeg import FFmpegPostProcessor


class SponsorBlockPP(FFmpegPostProcessor):
    # https://wiki.sponsor.ajay.app/w/Types
    EXTRACTORS = {
        'Youtube': 'YouTube',
    }
    POI_CATEGORIES = {
        'poi_highlight': 'Highlight',
    }
    NON_SKIPPABLE_CATEGORIES = {
        **POI_CATEGORIES,
        'chapter': 'Chapter',
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
        'hook': 'Hook/Greetings',
        **NON_SKIPPABLE_CATEGORIES,
    }

    def __init__(self, downloader, categories=None, api='https://sponsor.ajay.app'):
        FFmpegPostProcessor.__init__(self, downloader)
        self._categories = tuple(categories or self.CATEGORIES.keys())
        self._API_URL = api if re.match('https?://', api) else 'https://' + api

    def run(self, info):
        extractor = info['extractor_key']
        if extractor not in self.EXTRACTORS:
            self.to_screen(f'SponsorBlock is not supported for {extractor}')
            return [], info

        self.to_screen('Fetching SponsorBlock segments')
        info['sponsorblock_chapters'] = self._get_sponsor_chapters(info, info.get('duration'))
        return [], info

    def _get_sponsor_chapters(self, info, duration):
        segments = self._get_sponsor_segments(info['id'], self.EXTRACTORS[info['extractor_key']])

        def duration_filter(s):
            start_end = s['segment']
            # Ignore entire video segments (https://wiki.sponsor.ajay.app/w/Types).
            if start_end == (0, 0):
                return False
            # Ignore milliseconds difference at the start.
            if start_end[0] <= 1:
                start_end[0] = 0
            # Make POI chapters 1 sec so that we can properly mark them
            if s['category'] in self.POI_CATEGORIES:
                start_end[1] += 1
            # Ignore milliseconds difference at the end.
            # Never allow the segment to exceed the video.
            if duration and duration - start_end[1] <= 1:
                start_end[1] = duration
            # SponsorBlock duration may be absent or it may deviate from the real one.
            diff = abs(duration - s['videoDuration']) if s['videoDuration'] else 0
            return diff < 1 or (diff < 5 and diff / (start_end[1] - start_end[0]) < 0.05)

        duration_match = [s for s in segments if duration_filter(s)]
        if len(duration_match) != len(segments):
            self.report_warning('Some SponsorBlock segments are from a video of different duration, maybe from an old version of this video')

        def to_chapter(s):
            (start, end), cat = s['segment'], s['category']
            title = s['description'] if cat == 'chapter' else self.CATEGORIES[cat]
            return {
                'start_time': start,
                'end_time': end,
                'category': cat,
                'title': title,
                'type': s['actionType'],
                '_categories': [(cat, start, end, title)],
            }

        sponsor_chapters = [to_chapter(s) for s in duration_match]
        if not sponsor_chapters:
            self.to_screen('No matching segments were found in the SponsorBlock database')
        else:
            self.to_screen(f'Found {len(sponsor_chapters)} segments in the SponsorBlock database')
        return sponsor_chapters

    def _get_sponsor_segments(self, video_id, service):
        video_hash = hashlib.sha256(video_id.encode('ascii')).hexdigest()
        # SponsorBlock API recommends using first 4 hash characters.
        url = f'{self._API_URL}/api/skipSegments/{video_hash[:4]}?' + urllib.parse.urlencode({
            'service': service,
            'categories': json.dumps(self._categories),
            'actionTypes': json.dumps(['skip', 'poi', 'chapter']),
        })
        for d in self._download_json(url) or []:
            if d['videoID'] == video_id:
                return d['segments']
        return []
