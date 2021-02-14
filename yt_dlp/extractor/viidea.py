from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_HTTPError,
    compat_str,
    compat_urlparse,
)
from ..utils import (
    ExtractorError,
    js_to_json,
    parse_duration,
    parse_iso8601,
)


class ViideaIE(InfoExtractor):
    _VALID_URL = r'''(?x)https?://(?:www\.)?(?:
            videolectures\.net|
            flexilearn\.viidea\.net|
            presentations\.ocwconsortium\.org|
            video\.travel-zoom\.si|
            video\.pomp-forum\.si|
            tv\.nil\.si|
            video\.hekovnik.com|
            video\.szko\.si|
            kpk\.viidea\.com|
            inside\.viidea\.net|
            video\.kiberpipa\.org|
            bvvideo\.si|
            kongres\.viidea\.net|
            edemokracija\.viidea\.com
        )(?:/lecture)?/(?P<id>[^/]+)(?:/video/(?P<part>\d+))?/*(?:[#?].*)?$'''

    _TESTS = [{
        'url': 'http://videolectures.net/promogram_igor_mekjavic_eng/',
        'info_dict': {
            'id': '20171',
            'display_id': 'promogram_igor_mekjavic_eng',
            'ext': 'mp4',
            'title': 'Automatics, robotics and biocybernetics',
            'description': 'md5:815fc1deb6b3a2bff99de2d5325be482',
            'thumbnail': r're:http://.*\.jpg',
            'timestamp': 1372349289,
            'upload_date': '20130627',
            'duration': 565,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        # video with invalid direct format links (HTTP 403)
        'url': 'http://videolectures.net/russir2010_filippova_nlp/',
        'info_dict': {
            'id': '14891',
            'display_id': 'russir2010_filippova_nlp',
            'ext': 'flv',
            'title': 'NLP at Google',
            'description': 'md5:fc7a6d9bf0302d7cc0e53f7ca23747b3',
            'thumbnail': r're:http://.*\.jpg',
            'timestamp': 1284375600,
            'upload_date': '20100913',
            'duration': 5352,
        },
        'params': {
            # rtmp download
            'skip_download': True,
        },
    }, {
        # event playlist
        'url': 'http://videolectures.net/deeplearning2015_montreal/',
        'info_dict': {
            'id': '23181',
            'title': 'Deep Learning Summer School, Montreal 2015',
            'description': 'md5:0533a85e4bd918df52a01f0e1ebe87b7',
            'thumbnail': r're:http://.*\.jpg',
            'timestamp': 1438560000,
        },
        'playlist_count': 30,
    }, {
        # multi part lecture
        'url': 'http://videolectures.net/mlss09uk_bishop_ibi/',
        'info_dict': {
            'id': '9737',
            'display_id': 'mlss09uk_bishop_ibi',
            'title': 'Introduction To Bayesian Inference',
            'thumbnail': r're:http://.*\.jpg',
            'timestamp': 1251622800,
        },
        'playlist': [{
            'info_dict': {
                'id': '9737_part1',
                'display_id': 'mlss09uk_bishop_ibi_part1',
                'ext': 'wmv',
                'title': 'Introduction To Bayesian Inference (Part 1)',
                'thumbnail': r're:http://.*\.jpg',
                'duration': 4622,
                'timestamp': 1251622800,
                'upload_date': '20090830',
            },
        }, {
            'info_dict': {
                'id': '9737_part2',
                'display_id': 'mlss09uk_bishop_ibi_part2',
                'ext': 'wmv',
                'title': 'Introduction To Bayesian Inference (Part 2)',
                'thumbnail': r're:http://.*\.jpg',
                'duration': 5641,
                'timestamp': 1251622800,
                'upload_date': '20090830',
            },
        }],
        'playlist_count': 2,
    }]

    def _real_extract(self, url):
        lecture_slug, explicit_part_id = re.match(self._VALID_URL, url).groups()

        webpage = self._download_webpage(url, lecture_slug)

        cfg = self._parse_json(self._search_regex(
            [r'cfg\s*:\s*({.+?})\s*,\s*[\da-zA-Z_]+\s*:\s*\(?\s*function',
             r'cfg\s*:\s*({[^}]+})'],
            webpage, 'cfg'), lecture_slug, js_to_json)

        lecture_id = compat_str(cfg['obj_id'])

        base_url = self._proto_relative_url(cfg['livepipe'], 'http:')

        try:
            lecture_data = self._download_json(
                '%s/site/api/lecture/%s?format=json' % (base_url, lecture_id),
                lecture_id)['lecture'][0]
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                msg = self._parse_json(
                    e.cause.read().decode('utf-8'), lecture_id)
                raise ExtractorError(msg['detail'], expected=True)
            raise

        lecture_info = {
            'id': lecture_id,
            'display_id': lecture_slug,
            'title': lecture_data['title'],
            'timestamp': parse_iso8601(lecture_data.get('time')),
            'description': lecture_data.get('description_wiki'),
            'thumbnail': lecture_data.get('thumb'),
        }

        playlist_entries = []
        lecture_type = lecture_data.get('type')
        parts = [compat_str(video) for video in cfg.get('videos', [])]
        if parts:
            multipart = len(parts) > 1

            def extract_part(part_id):
                smil_url = '%s/%s/video/%s/smil.xml' % (base_url, lecture_slug, part_id)
                smil = self._download_smil(smil_url, lecture_id)
                info = self._parse_smil(smil, smil_url, lecture_id)
                self._sort_formats(info['formats'])
                info['id'] = lecture_id if not multipart else '%s_part%s' % (lecture_id, part_id)
                info['display_id'] = lecture_slug if not multipart else '%s_part%s' % (lecture_slug, part_id)
                if multipart:
                    info['title'] += ' (Part %s)' % part_id
                switch = smil.find('.//switch')
                if switch is not None:
                    info['duration'] = parse_duration(switch.attrib.get('dur'))
                item_info = lecture_info.copy()
                item_info.update(info)
                return item_info

            if explicit_part_id or not multipart:
                result = extract_part(explicit_part_id or parts[0])
            else:
                result = {
                    '_type': 'multi_video',
                    'entries': [extract_part(part) for part in parts],
                }
                result.update(lecture_info)

            # Immediately return explicitly requested part or non event item
            if explicit_part_id or lecture_type != 'evt':
                return result

            playlist_entries.append(result)

        # It's probably a playlist
        if not parts or lecture_type == 'evt':
            playlist_webpage = self._download_webpage(
                '%s/site/ajax/drilldown/?id=%s' % (base_url, lecture_id), lecture_id)
            entries = [
                self.url_result(compat_urlparse.urljoin(url, video_url), 'Viidea')
                for _, video_url in re.findall(
                    r'<a[^>]+href=(["\'])(.+?)\1[^>]+id=["\']lec=\d+', playlist_webpage)]
            playlist_entries.extend(entries)

        playlist = self.playlist_result(playlist_entries, lecture_id)
        playlist.update(lecture_info)
        return playlist
