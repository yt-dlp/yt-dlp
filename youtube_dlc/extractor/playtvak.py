# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import (
    compat_urlparse,
    compat_urllib_parse_urlencode,
)
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_iso8601,
    qualities,
)


class PlaytvakIE(InfoExtractor):
    IE_DESC = 'Playtvak.cz, iDNES.cz and Lidovky.cz'
    _VALID_URL = r'https?://(?:.+?\.)?(?:playtvak|idnes|lidovky|metro)\.cz/.*\?(?:c|idvideo)=(?P<id>[^&]+)'
    _TESTS = [{
        'url': 'http://www.playtvak.cz/vyzente-vosy-a-srsne-ze-zahrady-dn5-/hodinovy-manzel.aspx?c=A150730_150323_hodinovy-manzel_kuko',
        'md5': '4525ae312c324b4be2f4603cc78ceb4a',
        'info_dict': {
            'id': 'A150730_150323_hodinovy-manzel_kuko',
            'ext': 'mp4',
            'title': 'Vyžeňte vosy a sršně ze zahrady',
            'description': 'md5:4436e61b7df227a093778efb7e373571',
            'thumbnail': r're:(?i)^https?://.*\.(?:jpg|png)$',
            'duration': 279,
            'timestamp': 1438732860,
            'upload_date': '20150805',
            'is_live': False,
        }
    }, {  # live video test
        'url': 'http://slowtv.playtvak.cz/planespotting-0pr-/planespotting.aspx?c=A150624_164934_planespotting_cat',
        'info_dict': {
            'id': 'A150624_164934_planespotting_cat',
            'ext': 'flv',
            'title': 're:^Planespotting [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': 'Sledujte provoz na ranveji Letiště Václava Havla v Praze',
            'is_live': True,
        },
        'params': {
            'skip_download': True,  # requires rtmpdump
        },
    }, {  # another live stream, this one without Misc.videoFLV
        'url': 'https://slowtv.playtvak.cz/zive-sledujte-vlaky-v-primem-prenosu-dwi-/hlavni-nadrazi.aspx?c=A151218_145728_hlavni-nadrazi_plap',
        'info_dict': {
            'id': 'A151218_145728_hlavni-nadrazi_plap',
            'ext': 'flv',
            'title': 're:^Hlavní nádraží [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'is_live': True,
        },
        'params': {
            'skip_download': True,  # requires rtmpdump
        },
    }, {  # idnes.cz
        'url': 'http://zpravy.idnes.cz/pes-zavreny-v-aute-rozbijeni-okynek-v-aute-fj5-/domaci.aspx?c=A150809_104116_domaci_pku',
        'md5': '819832ba33cd7016e58a6658577fe289',
        'info_dict': {
            'id': 'A150809_104116_domaci_pku',
            'ext': 'mp4',
            'title': 'Zavřeli jsme mraženou pizzu do auta. Upekla se',
            'description': 'md5:01e73f02329e2e5760bd5eed4d42e3c2',
            'thumbnail': r're:(?i)^https?://.*\.(?:jpg|png)$',
            'duration': 39,
            'timestamp': 1438969140,
            'upload_date': '20150807',
            'is_live': False,
        }
    }, {  # lidovky.cz
        'url': 'http://www.lidovky.cz/dalsi-demonstrace-v-praze-o-migraci-duq-/video.aspx?c=A150808_214044_ln-video_ELE',
        'md5': 'c7209ac4ba9d234d4ad5bab7485bcee8',
        'info_dict': {
            'id': 'A150808_214044_ln-video_ELE',
            'ext': 'mp4',
            'title': 'Táhni! Demonstrace proti imigrantům budila emoce',
            'description': 'md5:97c81d589a9491fbfa323c9fa3cca72c',
            'thumbnail': r're:(?i)^https?://.*\.(?:jpg|png)$',
            'timestamp': 1439052180,
            'upload_date': '20150808',
            'is_live': False,
        }
    }, {  # metro.cz
        'url': 'http://www.metro.cz/video-pod-billboardem-se-na-vltavske-roztocil-kolotoc-deti-vozil-jen-par-hodin-1hx-/metro-extra.aspx?c=A141111_173251_metro-extra_row',
        'md5': '84fc1deedcac37b7d4a6ccae7c716668',
        'info_dict': {
            'id': 'A141111_173251_metro-extra_row',
            'ext': 'mp4',
            'title': 'Recesisté udělali z billboardu kolotoč',
            'description': 'md5:7369926049588c3989a66c9c1a043c4c',
            'thumbnail': r're:(?i)^https?://.*\.(?:jpg|png)$',
            'timestamp': 1415725500,
            'upload_date': '20141111',
            'is_live': False,
        }
    }, {
        'url': 'http://www.playtvak.cz/embed.aspx?idvideo=V150729_141549_play-porad_kuko',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        info_url = self._html_search_regex(
            r'Misc\.video(?:FLV)?\(\s*{\s*data\s*:\s*"([^"]+)"', webpage, 'info url')

        parsed_url = compat_urlparse.urlparse(info_url)

        qs = compat_urlparse.parse_qs(parsed_url.query)
        qs.update({
            'reklama': ['0'],
            'type': ['js'],
        })

        info_url = compat_urlparse.urlunparse(
            parsed_url._replace(query=compat_urllib_parse_urlencode(qs, True)))

        json_info = self._download_json(
            info_url, video_id,
            transform_source=lambda s: s[s.index('{'):s.rindex('}') + 1])

        item = None
        for i in json_info['items']:
            if i.get('type') == 'video' or i.get('type') == 'stream':
                item = i
                break
        if not item:
            raise ExtractorError('No suitable stream found')

        quality = qualities(('low', 'middle', 'high'))

        formats = []
        for fmt in item['video']:
            video_url = fmt.get('file')
            if not video_url:
                continue

            format_ = fmt['format']
            format_id = '%s_%s' % (format_, fmt['quality'])
            preference = None

            if format_ in ('mp4', 'webm'):
                ext = format_
            elif format_ == 'rtmp':
                ext = 'flv'
            elif format_ == 'apple':
                ext = 'mp4'
                # Some streams have mp3 audio which does not play
                # well with ffmpeg filter aac_adtstoasc
                preference = -10
            elif format_ == 'adobe':  # f4m manifest fails with 404 in 80% of requests
                continue
            else:  # Other formats not supported yet
                continue

            formats.append({
                'url': video_url,
                'ext': ext,
                'format_id': format_id,
                'quality': quality(fmt.get('quality')),
                'preference': preference,
            })
        self._sort_formats(formats)

        title = item['title']
        is_live = item['type'] == 'stream'
        if is_live:
            title = self._live_title(title)
        description = self._og_search_description(webpage, default=None) or self._html_search_meta(
            'description', webpage, 'description', default=None)
        timestamp = None
        duration = None
        if not is_live:
            duration = int_or_none(item.get('length'))
            timestamp = item.get('published')
            if timestamp:
                timestamp = parse_iso8601(timestamp[:-5])

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': item.get('image'),
            'duration': duration,
            'timestamp': timestamp,
            'is_live': is_live,
            'formats': formats,
        }
