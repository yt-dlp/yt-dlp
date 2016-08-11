# coding: ISO-8859-15
from __future__ import unicode_literals
from datetime import (
    datetime,
    timedelta,
)

from .common import InfoExtractor
from ..utils import (
    update_url_query,
    xpath_text,
    str_to_int,
    int_or_none,
    HEADRequest,
    unescapeHTML,
)

import re


class Kanal2IE(InfoExtractor):
    _VALID_URL = r'(?P<base>https?:\/\/.+\.postimees\.ee)[a-zA-Z0-9\/._-]+\?[a-zA-Z0-9=&._-]*id=(?P<id>[a-zA-Z0-9_-]+)[^ ]*'
    _TESTS = [{
        # The most ordinary case
        'url': 'http://kanal2.postimees.ee/pluss/video/?id=40792',
        'md5': '173e29daea5f5fab49390bddd78aaaf0',
        'info_dict': {
            'id': '40792',
            'ext': 'flv',
            'title': 'Aedniku aabits (06.08.2016 10:30)',
            'thumbnail': 'http://kanal2.postimees.ee/imagecache/http_img.cdn.mind.ee/kanal2//14/100/00033/0053_4468c974c1010a21817c1ee37f3e7902.jpeg',
            'description': 'Aedniku aabits" on saade, mis pakub kaasaelamist ja teadmisi nii algajatele, kui juba kogenud rohenäppudele. Kõik alates vajalikest näpunäidetest, nutikatest lahendustest, uudistoodetest kuni taimede hingeeluni ning aias kasutatava tehnikani välja.',
            'upload_date': '20160805',
            'timestamp': 1470434400,
        }
    }, {
        # Embed player, also needs login in reality but all the streams are accessable without logging in
        'url': 'http://kanal2.postimees.ee/video/lonelyPlayer?videoid=28848',
        'md5': '18edb2fd235c06a60b81b3590a357ace',
        'info_dict': {
            'id': '28848',
            'ext': 'flv',
            'title': 'Viimane võmm - Rita, ära jama (24.11.2015 21:30)',
            'thumbnail': 'http://kanal2.postimees.ee/imagecache/http_img.cdn.mind.ee/kanal2//14/100/00002/0050_4468c974c1010a21817c1ee37f3e7902.jpeg',
            'description': 'Kinnisvaraomanik Villem Meius leitakse oma korterist tapetuna. Turvakaamera video paljastab surnukeha kõrvalt lahkumas ühe Meiuse üürniku - ei kellegi muu, kui politseinike kaitseingli Rita! Rita võetakse vahi alla ning kogu jaoskond näeb vaeva selle nimel, et teda vabastada ning tema kinniistumise ajal Rita baari käigus hoida. Uurimise käigus paljastub ulatuslik ja häbitu kinnisvarahangeldamine Kalamajas, mille niidid ulatuvad ka justiitsmaailma ladvikusse. Vastasleeri moodustavad Kalamaja põliselanikud. Organisatsiooni peakorter asub kellegi Mort Pärgi matusebüroos. Sealt hakkabki asi lõpuks hargnema.'
        }
    }, {
        # Other ordinary case
        'url': 'http://kanal2.postimees.ee/pluss/preview?id=40744',
        'md5': '2579cdbf16013d7e7a7361a832bc818e',
        'info_dict': {
            'id': '40744',
            'ext': 'flv',
            'title': 'Kaunis Dila (10.08.2016 19:00)',
            'thumbnail': 'http://kanal2.postimees.ee/imagecache/http_img.cdn.mind.ee/kanal2//16/300/00208/0050_4468c974c1010a21817c1ee37f3e7902.jpeg',
        }
    }, {
        # Not on kanal2 subdomain like others, the site has different layout, so a lot of data can't be accessed, but the api's are same. also has rating
        'url': 'http://kanal12.postimees.ee/vaatasaateid/Punkri-joulueri?videoid=248',
        'md5': '4633c310980201e4d8195d22b948ad10',
        'info_dict': {
            'id': '248',
            'ext': 'flv',
            'title': 'Punkri jõulueri',
            'thumbnail': 'http://img.cdn.mind.ee/kanal2/clips/KANAL 12/punkri joulueri.jpeg',
            'description': 'Eestlaste lemmik-krõbesaade lõpetab aasta loodetavasti südamliku pühade-eriga! Hapukapsad ninast välja! Jeesuse sündi on tulnud tähistama Ivo Linna, pastor, saatan ja paljud teised. Saadet juhivad Marge Tava, Aleksander Ots ja Marek Reinaas.',
            'average_rating': int,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        base = re.compile(self._VALID_URL).match(url).group('base')
        if "pluss" not in url and "kanal2" in base:
            url = base + '/pluss/video/?id=' + video_id
            # This part copied from generic.py, bypasses redirects
            head_response = self._request_webpage(HEADRequest(url), video_id)
            if head_response is not False:
                new_url = head_response.geturl()
                if url != new_url:
                    self._downloader.to_screen('[redirect] Following redirect to %s' % new_url)
                return self.url_result(new_url)

        xmlfile = self._download_xml(update_url_query(base + '/video/playerPlaylistApi', {'id': video_id}), video_id)
        host = xmlfile.find('./playlist/video/streamItems').get('host')

        formats = [{
            'protocol': re.compile('(?P<protocol>.+):\/\/[^\0]*').match(host).group('protocol') or 'rtmp',
            'app': re.compile(((re.compile('(?P<protocol>.+):\/\/[^\0]*').match(host).group('protocol') or 'rtmp') + ':\/\/[^\0]*\/(?P<app>.+\/)')).match(host).group('app') or 'kanal2vod',
            'url': host + stream.get('streamName'),
            'play_path': 'mp4:' + stream.get('streamName'),
            'ext': 'flv',
            'height': str_to_int(stream.get('height')),
            'width': str_to_int(stream.get('width')),
            'rtmp_real_time': True,
        } for stream in xmlfile.findall('./playlist/video/streamItems/streamItem')]
        self._sort_formats(formats)

        # Remove stacked urls(e.g. http://test.comhttp://test2.com, removes everything before second http(kanal12 fix))
        thumbnail = re.compile('[^\0]*(?P<realurl>https?:\/\/[^"]+)[^\0]*').match(base + xpath_text(xmlfile, './playlist/video/thumbUrl')).group('realurl')
        average_rating = int_or_none(xpath_text(xmlfile, './playlist/video/rating/value'))

        webpage = self._download_webpage(url, video_id)
        if 'player-container' in webpage:
            description = self._search_regex(r'[^\0]*<p class="full"[^>]*>([^<]*)<\/p>[^\0]*', webpage, 'description', default=None)
            if description is not None:
                description = description.strip()

            epandseasonregex = re.compile('Osa *(?P<episode>[0-9]+) *Hooaeg *(?P<season>[0-9]+)').match(self._search_regex('[^\0]*(Osa *[0-9]+ *Hooaeg *[0-9]+)[^\0]*', webpage, 'epandseason', default=None))
            if epandseasonregex is not None:
                episode = int_or_none(epandseasonregex.group('episode'))
                season = int_or_none(epandseasonregex.group('season'))

            dateandtimeregex = re.compile('[^\0]*eetris[^\0]*<\/span>[^\0]*(?P<date>[0-9]{1,2}.[0-9]{1,2}.[0-9]{4,})[^0-9]*(?P<time>[0-9]{1,2}:[0-9]{1,2})[^\0]*').match(self._search_regex('[^\0]*(eetris[^\0]*<\/span>[^\0]*[0-9]{1,2}.[0-9]{1,2}.[0-9]{4,}[^0-9]*[0-9]{1,2}:[0-9]{1,2})[^\0]*', webpage, 'dateandtime', default=None))
            if dateandtimeregex is not None:
                date = dateandtimeregex.group('date')
                time = dateandtimeregex.group('time')
                timestamp = int_or_none((datetime.strptime(date + " " + time, '%d.%m.%Y %H:%M') - datetime(1970, 1, 1) + timedelta(seconds=60 * 60 * 2)).total_seconds())  # No dst support, but added the 2 default hours of estonia
            player_url = self._search_regex('[^\0]embedSWF\("([^"]+)[^\0]', webpage, 'player_url', default=None)

        else:
            description = None
            player_url = None
            season = None
            episode = None
            timestamp = None

        if description is None:
            description = xpath_text(xmlfile, './playlist/video/description') or self._search_regex('[^\0]og:description" *content="(.*)\" *\/>', webpage, 'description', default=None)
            if description is not None:
                description = unescapeHTML(description).strip()

        if episode is None:
            episode = int_or_none(xpath_text(xmlfile, './playlist/video/episode'))

        title = xpath_text(xmlfile, './playlist/video/name')
        if title is None:
            title = self._search_regex('[^\0]og:title" *content="(.*)\" *\/>', webpage, 'title', default=None) or self._search_regex('[^\0]<title>(.*)<\/title>[^\0]', webpage, 'description', default=None)

        return {
            'average_rating': average_rating,
            'description': description,
            'episode_number': episode,
            'formats': formats,
            'id': video_id,
            'page_url': url,
            'player_url': player_url,
            'season_number': season,
            'timestamp': timestamp,
            'title': title,
            'thumbnail': thumbnail,
        }
