from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_duration,
    remove_end,
    xpath_element,
    xpath_text,
)


class DigitallySpeakingIE(InfoExtractor):
    _VALID_URL = r'https?://(?:s?evt\.dispeak|events\.digitallyspeaking)\.com/(?:[^/]+/)+xml/(?P<id>[^.]+)\.xml'

    _TESTS = [{
        # From http://gdcvault.com/play/1023460/Tenacious-Design-and-The-Interface
        'url': 'http://evt.dispeak.com/ubm/gdc/sf16/xml/840376_BQRC.xml',
        'md5': 'a8efb6c31ed06ca8739294960b2dbabd',
        'info_dict': {
            'id': '840376_BQRC',
            'ext': 'mp4',
            'title': 'Tenacious Design and The Interface of \'Destiny\'',
        },
    }, {
        # From http://www.gdcvault.com/play/1014631/Classic-Game-Postmortem-PAC
        'url': 'http://events.digitallyspeaking.com/gdc/sf11/xml/12396_1299111843500GMPX.xml',
        'only_matching': True,
    }, {
        # From http://www.gdcvault.com/play/1013700/Advanced-Material
        'url': 'http://sevt.dispeak.com/ubm/gdc/eur10/xml/11256_1282118587281VNIT.xml',
        'only_matching': True,
    }]

    def _parse_mp4(self, metadata):
        video_formats = []
        video_root = None

        mp4_video = xpath_text(metadata, './mp4video', default=None)
        if mp4_video is not None:
            mobj = re.match(r'(?P<root>https?://.*?/).*', mp4_video)
            video_root = mobj.group('root')
        if video_root is None:
            http_host = xpath_text(metadata, 'httpHost', default=None)
            if http_host:
                video_root = 'http://%s/' % http_host
        if video_root is None:
            # Hard-coded in http://evt.dispeak.com/ubm/gdc/sf16/custom/player2.js
            # Works for GPUTechConf, too
            video_root = 'http://s3-2u.digitallyspeaking.com/'

        formats = metadata.findall('./MBRVideos/MBRVideo')
        if not formats:
            return None
        for a_format in formats:
            stream_name = xpath_text(a_format, 'streamName', fatal=True)
            video_path = re.match(r'mp4\:(?P<path>.*)', stream_name).group('path')
            url = video_root + video_path
            bitrate = xpath_text(a_format, 'bitrate')
            tbr = int_or_none(bitrate)
            vbr = int_or_none(self._search_regex(
                r'-(\d+)\.mp4', video_path, 'vbr', default=None))
            abr = tbr - vbr if tbr and vbr else None
            video_formats.append({
                'format_id': bitrate,
                'url': url,
                'tbr': tbr,
                'vbr': vbr,
                'abr': abr,
            })
        return video_formats

    def _parse_flv(self, metadata):
        formats = []
        akamai_url = xpath_text(metadata, './akamaiHost', fatal=True)
        audios = metadata.findall('./audios/audio')
        for audio in audios:
            formats.append({
                'url': 'rtmp://%s/ondemand?ovpfv=1.1' % akamai_url,
                'play_path': remove_end(audio.get('url'), '.flv'),
                'ext': 'flv',
                'vcodec': 'none',
                'quality': 1,
                'format_id': audio.get('code'),
            })
        slide_video_path = xpath_text(metadata, './slideVideo', fatal=True)
        formats.append({
            'url': 'rtmp://%s/ondemand?ovpfv=1.1' % akamai_url,
            'play_path': remove_end(slide_video_path, '.flv'),
            'ext': 'flv',
            'format_note': 'slide deck video',
            'quality': -2,
            'format_id': 'slides',
            'acodec': 'none',
        })
        speaker_video_path = xpath_text(metadata, './speakerVideo', fatal=True)
        formats.append({
            'url': 'rtmp://%s/ondemand?ovpfv=1.1' % akamai_url,
            'play_path': remove_end(speaker_video_path, '.flv'),
            'ext': 'flv',
            'format_note': 'speaker video',
            'quality': -1,
            'format_id': 'speaker',
        })
        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)

        xml_description = self._download_xml(url, video_id)
        metadata = xpath_element(xml_description, 'metadata')

        video_formats = self._parse_mp4(metadata)
        if video_formats is None:
            video_formats = self._parse_flv(metadata)

        return {
            'id': video_id,
            'formats': video_formats,
            'title': xpath_text(metadata, 'title', fatal=True),
            'duration': parse_duration(xpath_text(metadata, 'endTime')),
            'creator': xpath_text(metadata, 'speaker'),
        }
