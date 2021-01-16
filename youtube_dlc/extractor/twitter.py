# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_HTTPError,
    compat_parse_qs,
    compat_urllib_parse_unquote,
    compat_urllib_parse_urlparse,
)
from ..utils import (
    dict_get,
    ExtractorError,
    float_or_none,
    int_or_none,
    try_get,
    strip_or_none,
    unified_timestamp,
    update_url_query,
    xpath_text,
)

from .periscope import (
    PeriscopeBaseIE,
    PeriscopeIE,
)


class TwitterBaseIE(InfoExtractor):
    _API_BASE = 'https://api.twitter.com/1.1/'
    _BASE_REGEX = r'https?://(?:(?:www|m(?:obile)?)\.)?twitter\.com/'
    _GUEST_TOKEN = None

    def _extract_variant_formats(self, variant, video_id):
        variant_url = variant.get('url')
        if not variant_url:
            return []
        elif '.m3u8' in variant_url:
            return self._extract_m3u8_formats(
                variant_url, video_id, 'mp4', 'm3u8_native',
                m3u8_id='hls', fatal=False)
        else:
            tbr = int_or_none(dict_get(variant, ('bitrate', 'bit_rate')), 1000) or None
            f = {
                'url': variant_url,
                'format_id': 'http' + ('-%d' % tbr if tbr else ''),
                'tbr': tbr,
            }
            self._search_dimensions_in_video_url(f, variant_url)
            return [f]

    def _extract_formats_from_vmap_url(self, vmap_url, video_id):
        vmap_data = self._download_xml(vmap_url, video_id)
        formats = []
        urls = []
        for video_variant in vmap_data.findall('.//{http://twitter.com/schema/videoVMapV2.xsd}videoVariant'):
            video_variant.attrib['url'] = compat_urllib_parse_unquote(
                video_variant.attrib['url'])
            urls.append(video_variant.attrib['url'])
            formats.extend(self._extract_variant_formats(
                video_variant.attrib, video_id))
        video_url = strip_or_none(xpath_text(vmap_data, './/MediaFile'))
        if video_url not in urls:
            formats.extend(self._extract_variant_formats({'url': video_url}, video_id))
        return formats

    @staticmethod
    def _search_dimensions_in_video_url(a_format, video_url):
        m = re.search(r'/(?P<width>\d+)x(?P<height>\d+)/', video_url)
        if m:
            a_format.update({
                'width': int(m.group('width')),
                'height': int(m.group('height')),
            })

    def _call_api(self, path, video_id, query={}):
        headers = {
            'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAAPYXBAAAAAAACLXUNDekMxqa8h%2F40K4moUkGsoc%3DTYfbDKbT3jJPCEVnMYqilB28NHfOPqkca3qaAxGfsyKCs0wRbw',
        }
        if not self._GUEST_TOKEN:
            self._GUEST_TOKEN = self._download_json(
                self._API_BASE + 'guest/activate.json', video_id,
                'Downloading guest token', data=b'',
                headers=headers)['guest_token']
        headers['x-guest-token'] = self._GUEST_TOKEN
        try:
            return self._download_json(
                self._API_BASE + path, video_id, headers=headers, query=query)
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                raise ExtractorError(self._parse_json(
                    e.cause.read().decode(),
                    video_id)['errors'][0]['message'], expected=True)
            raise


class TwitterCardIE(InfoExtractor):
    IE_NAME = 'twitter:card'
    _VALID_URL = TwitterBaseIE._BASE_REGEX + r'i/(?:cards/tfw/v1|videos(?:/tweet)?)/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://twitter.com/i/cards/tfw/v1/560070183650213889',
            # MD5 checksums are different in different places
            'info_dict': {
                'id': '560070183650213889',
                'ext': 'mp4',
                'title': "Twitter - You can now shoot, edit and share video on Twitter. Capture life's most moving moments from your perspective.",
                'description': 'md5:18d3e24bb4f6e5007487dd546e53bd96',
                'uploader': 'Twitter',
                'uploader_id': 'Twitter',
                'thumbnail': r're:^https?://.*\.jpg',
                'duration': 30.033,
                'timestamp': 1422366112,
                'upload_date': '20150127',
            },
        },
        {
            'url': 'https://twitter.com/i/cards/tfw/v1/623160978427936768',
            'md5': '7137eca597f72b9abbe61e5ae0161399',
            'info_dict': {
                'id': '623160978427936768',
                'ext': 'mp4',
                'title': "NASA - Fly over Pluto's icy Norgay Mountains and Sputnik Plain in this @NASANewHorizons #PlutoFlyby video.",
                'description': "Fly over Pluto's icy Norgay Mountains and Sputnik Plain in this @NASANewHorizons #PlutoFlyby video. https://t.co/BJYgOjSeGA",
                'uploader': 'NASA',
                'uploader_id': 'NASA',
                'timestamp': 1437408129,
                'upload_date': '20150720',
            },
        },
        {
            'url': 'https://twitter.com/i/cards/tfw/v1/654001591733886977',
            'md5': 'b6d9683dd3f48e340ded81c0e917ad46',
            'info_dict': {
                'id': 'dq4Oj5quskI',
                'ext': 'mp4',
                'title': 'Ubuntu 11.10 Overview',
                'description': 'md5:a831e97fa384863d6e26ce48d1c43376',
                'upload_date': '20111013',
                'uploader': 'OMG! UBUNTU!',
                'uploader_id': 'omgubuntu',
            },
            'add_ie': ['Youtube'],
        },
        {
            'url': 'https://twitter.com/i/cards/tfw/v1/665289828897005568',
            'md5': '6dabeaca9e68cbb71c99c322a4b42a11',
            'info_dict': {
                'id': 'iBb2x00UVlv',
                'ext': 'mp4',
                'upload_date': '20151113',
                'uploader_id': '1189339351084113920',
                'uploader': 'ArsenalTerje',
                'title': 'Vine by ArsenalTerje',
                'timestamp': 1447451307,
            },
            'add_ie': ['Vine'],
        }, {
            'url': 'https://twitter.com/i/videos/tweet/705235433198714880',
            'md5': '884812a2adc8aaf6fe52b15ccbfa3b88',
            'info_dict': {
                'id': '705235433198714880',
                'ext': 'mp4',
                'title': "Brent Yarina - Khalil Iverson's missed highlight dunk. And made highlight dunk. In one highlight.",
                'description': "Khalil Iverson's missed highlight dunk. And made highlight dunk. In one highlight. https://t.co/OrxcJ28Bns",
                'uploader': 'Brent Yarina',
                'uploader_id': 'BTNBrentYarina',
                'timestamp': 1456976204,
                'upload_date': '20160303',
            },
            'skip': 'This content is no longer available.',
        }, {
            'url': 'https://twitter.com/i/videos/752274308186120192',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        status_id = self._match_id(url)
        return self.url_result(
            'https://twitter.com/statuses/' + status_id,
            TwitterIE.ie_key(), status_id)


class TwitterIE(TwitterBaseIE):
    IE_NAME = 'twitter'
    _VALID_URL = TwitterBaseIE._BASE_REGEX + r'(?:(?:i/web|[^/]+)/status|statuses)/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://twitter.com/freethenipple/status/643211948184596480',
        'info_dict': {
            'id': '643211948184596480',
            'ext': 'mp4',
            'title': 'FREE THE NIPPLE - FTN supporters on Hollywood Blvd today!',
            'thumbnail': r're:^https?://.*\.jpg',
            'description': 'FTN supporters on Hollywood Blvd today! http://t.co/c7jHH749xJ',
            'uploader': 'FREE THE NIPPLE',
            'uploader_id': 'freethenipple',
            'duration': 12.922,
            'timestamp': 1442188653,
            'upload_date': '20150913',
            'age_limit': 18,
        },
    }, {
        'url': 'https://twitter.com/giphz/status/657991469417025536/photo/1',
        'md5': 'f36dcd5fb92bf7057f155e7d927eeb42',
        'info_dict': {
            'id': '657991469417025536',
            'ext': 'mp4',
            'title': 'Gifs - tu vai cai tu vai cai tu nao eh capaz disso tu vai cai',
            'description': 'Gifs on Twitter: "tu vai cai tu vai cai tu nao eh capaz disso tu vai cai https://t.co/tM46VHFlO5"',
            'thumbnail': r're:^https?://.*\.png',
            'uploader': 'Gifs',
            'uploader_id': 'giphz',
        },
        'expected_warnings': ['height', 'width'],
        'skip': 'Account suspended',
    }, {
        'url': 'https://twitter.com/starwars/status/665052190608723968',
        'info_dict': {
            'id': '665052190608723968',
            'ext': 'mp4',
            'title': 'Star Wars - A new beginning is coming December 18. Watch the official 60 second #TV spot for #StarWars: #TheForceAwakens.',
            'description': 'A new beginning is coming December 18. Watch the official 60 second #TV spot for #StarWars: #TheForceAwakens. https://t.co/OkSqT2fjWJ',
            'uploader_id': 'starwars',
            'uploader': 'Star Wars',
            'timestamp': 1447395772,
            'upload_date': '20151113',
        },
    }, {
        'url': 'https://twitter.com/BTNBrentYarina/status/705235433198714880',
        'info_dict': {
            'id': '705235433198714880',
            'ext': 'mp4',
            'title': "Brent Yarina - Khalil Iverson's missed highlight dunk. And made highlight dunk. In one highlight.",
            'description': "Khalil Iverson's missed highlight dunk. And made highlight dunk. In one highlight. https://t.co/OrxcJ28Bns",
            'uploader_id': 'BTNBrentYarina',
            'uploader': 'Brent Yarina',
            'timestamp': 1456976204,
            'upload_date': '20160303',
        },
        'params': {
            # The same video as https://twitter.com/i/videos/tweet/705235433198714880
            # Test case of TwitterCardIE
            'skip_download': True,
        },
    }, {
        'url': 'https://twitter.com/jaydingeer/status/700207533655363584',
        'info_dict': {
            'id': '700207533655363584',
            'ext': 'mp4',
            'title': 'simon vertugo - BEAT PROD: @suhmeduh #Damndaniel',
            'description': 'BEAT PROD: @suhmeduh  https://t.co/HBrQ4AfpvZ #Damndaniel https://t.co/byBooq2ejZ',
            'thumbnail': r're:^https?://.*\.jpg',
            'uploader': 'simon vertugo',
            'uploader_id': 'simonvertugo',
            'duration': 30.0,
            'timestamp': 1455777459,
            'upload_date': '20160218',
        },
    }, {
        'url': 'https://twitter.com/Filmdrunk/status/713801302971588609',
        'md5': '89a15ed345d13b86e9a5a5e051fa308a',
        'info_dict': {
            'id': 'MIOxnrUteUd',
            'ext': 'mp4',
            'title': 'Dr.Pepperの飲み方 #japanese #バカ #ドクペ #電動ガン',
            'uploader': 'TAKUMA',
            'uploader_id': '1004126642786242560',
            'timestamp': 1402826626,
            'upload_date': '20140615',
        },
        'add_ie': ['Vine'],
    }, {
        'url': 'https://twitter.com/captainamerica/status/719944021058060289',
        'info_dict': {
            'id': '719944021058060289',
            'ext': 'mp4',
            'title': 'Captain America - @King0fNerd Are you sure you made the right choice? Find out in theaters.',
            'description': '@King0fNerd Are you sure you made the right choice? Find out in theaters. https://t.co/GpgYi9xMJI',
            'uploader_id': 'CaptainAmerica',
            'uploader': 'Captain America',
            'duration': 3.17,
            'timestamp': 1460483005,
            'upload_date': '20160412',
        },
    }, {
        'url': 'https://twitter.com/OPP_HSD/status/779210622571536384',
        'info_dict': {
            'id': '1zqKVVlkqLaKB',
            'ext': 'mp4',
            'title': 'Sgt Kerry Schmidt - Ontario Provincial Police - Road rage, mischief, assault, rollover and fire in one occurrence',
            'upload_date': '20160923',
            'uploader_id': '1PmKqpJdOJQoY',
            'uploader': 'Sgt Kerry Schmidt - Ontario Provincial Police',
            'timestamp': 1474613214,
        },
        'add_ie': ['Periscope'],
    }, {
        # has mp4 formats via mobile API
        'url': 'https://twitter.com/news_al3alm/status/852138619213144067',
        'info_dict': {
            'id': '852138619213144067',
            'ext': 'mp4',
            'title': 'عالم الأخبار - كلمة تاريخية بجلسة الجناسي التاريخية.. النائب خالد مؤنس العتيبي للمعارضين : اتقوا الله .. الظلم ظلمات يوم القيامة',
            'description': 'كلمة تاريخية بجلسة الجناسي التاريخية.. النائب خالد مؤنس العتيبي للمعارضين : اتقوا الله .. الظلم ظلمات يوم القيامة   https://t.co/xg6OhpyKfN',
            'uploader': 'عالم الأخبار',
            'uploader_id': 'news_al3alm',
            'duration': 277.4,
            'timestamp': 1492000653,
            'upload_date': '20170412',
        },
        'skip': 'Account suspended',
    }, {
        'url': 'https://twitter.com/i/web/status/910031516746514432',
        'info_dict': {
            'id': '910031516746514432',
            'ext': 'mp4',
            'title': 'Préfet de Guadeloupe - [Direct] #Maria Le centre se trouve actuellement au sud de Basse-Terre. Restez confinés. Réfugiez-vous dans la pièce la + sûre.',
            'thumbnail': r're:^https?://.*\.jpg',
            'description': '[Direct] #Maria Le centre se trouve actuellement au sud de Basse-Terre. Restez confinés. Réfugiez-vous dans la pièce la + sûre. https://t.co/mwx01Rs4lo',
            'uploader': 'Préfet de Guadeloupe',
            'uploader_id': 'Prefet971',
            'duration': 47.48,
            'timestamp': 1505803395,
            'upload_date': '20170919',
        },
        'params': {
            'skip_download': True,  # requires ffmpeg
        },
    }, {
        # card via api.twitter.com/1.1/videos/tweet/config
        'url': 'https://twitter.com/LisPower1/status/1001551623938805763',
        'info_dict': {
            'id': '1001551623938805763',
            'ext': 'mp4',
            'title': 're:.*?Shep is on a roll today.*?',
            'thumbnail': r're:^https?://.*\.jpg',
            'description': 'md5:37b9f2ff31720cef23b2bd42ee8a0f09',
            'uploader': 'Lis Power',
            'uploader_id': 'LisPower1',
            'duration': 111.278,
            'timestamp': 1527623489,
            'upload_date': '20180529',
        },
        'params': {
            'skip_download': True,  # requires ffmpeg
        },
    }, {
        'url': 'https://twitter.com/foobar/status/1087791357756956680',
        'info_dict': {
            'id': '1087791357756956680',
            'ext': 'mp4',
            'title': 'Twitter - A new is coming.  Some of you got an opt-in to try it now. Check out the emoji button, quick keyboard shortcuts, upgraded trends, advanced search, and more. Let us know your thoughts!',
            'thumbnail': r're:^https?://.*\.jpg',
            'description': 'md5:6dfd341a3310fb97d80d2bf7145df976',
            'uploader': 'Twitter',
            'uploader_id': 'Twitter',
            'duration': 61.567,
            'timestamp': 1548184644,
            'upload_date': '20190122',
        },
    }, {
        # not available in Periscope
        'url': 'https://twitter.com/ViviEducation/status/1136534865145286656',
        'info_dict': {
            'id': '1vOGwqejwoWxB',
            'ext': 'mp4',
            'title': 'Vivi - Vivi founder @lior_rauchy announcing our new student feedback tool live at @EduTECH_AU #EduTECH2019',
            'uploader': 'Vivi',
            'uploader_id': '1eVjYOLGkGrQL',
        },
        'add_ie': ['TwitterBroadcast'],
    }, {
        # unified card
        'url': 'https://twitter.com/BrooklynNets/status/1349794411333394432?s=20',
        'info_dict': {
            'id': '1349794411333394432',
            'ext': 'mp4',
            'title': 'md5:d1c4941658e4caaa6cb579260d85dcba',
            'thumbnail': r're:^https?://.*\.jpg',
            'description': 'md5:71ead15ec44cee55071547d6447c6a3e',
            'uploader': 'Brooklyn Nets',
            'uploader_id': 'BrooklynNets',
            'duration': 324.484,
            'timestamp': 1610651040,
            'upload_date': '20210114',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # Twitch Clip Embed
        'url': 'https://twitter.com/GunB1g/status/1163218564784017422',
        'only_matching': True,
    }, {
        # promo_video_website card
        'url': 'https://twitter.com/GunB1g/status/1163218564784017422',
        'only_matching': True,
    }, {
        # promo_video_convo card
        'url': 'https://twitter.com/poco_dandy/status/1047395834013384704',
        'only_matching': True,
    }, {
        # appplayer card
        'url': 'https://twitter.com/poco_dandy/status/1150646424461176832',
        'only_matching': True,
    }, {
        # video_direct_message card
        'url': 'https://twitter.com/qarev001/status/1348948114569269251',
        'only_matching': True,
    }, {
        # poll2choice_video card
        'url': 'https://twitter.com/CAF_Online/status/1349365911120195585',
        'only_matching': True,
    }, {
        # poll3choice_video card
        'url': 'https://twitter.com/SamsungMobileSA/status/1348609186725289984',
        'only_matching': True,
    }, {
        # poll4choice_video card
        'url': 'https://twitter.com/SouthamptonFC/status/1347577658079641604',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        twid = self._match_id(url)
        status = self._call_api(
            'statuses/show/%s.json' % twid, twid, {
                'cards_platform': 'Web-12',
                'include_cards': 1,
                'include_reply_count': 1,
                'include_user_entities': 0,
                'tweet_mode': 'extended',
            })

        title = description = status['full_text'].replace('\n', ' ')
        # strip  'https -_t.co_BJYgOjSeGA' junk from filenames
        title = re.sub(r'\s+(https?://[^ ]+)', '', title)
        user = status.get('user') or {}
        uploader = user.get('name')
        if uploader:
            title = '%s - %s' % (uploader, title)
        uploader_id = user.get('screen_name')

        tags = []
        for hashtag in (try_get(status, lambda x: x['entities']['hashtags'], list) or []):
            hashtag_text = hashtag.get('text')
            if not hashtag_text:
                continue
            tags.append(hashtag_text)

        info = {
            'id': twid,
            'title': title,
            'description': description,
            'uploader': uploader,
            'timestamp': unified_timestamp(status.get('created_at')),
            'uploader_id': uploader_id,
            'uploader_url': 'https://twitter.com/' + uploader_id if uploader_id else None,
            'like_count': int_or_none(status.get('favorite_count')),
            'repost_count': int_or_none(status.get('retweet_count')),
            'comment_count': int_or_none(status.get('reply_count')),
            'age_limit': 18 if status.get('possibly_sensitive') else 0,
            'tags': tags,
        }

        def extract_from_video_info(media):
            video_info = media.get('video_info') or {}

            formats = []
            for variant in video_info.get('variants', []):
                formats.extend(self._extract_variant_formats(variant, twid))
            self._sort_formats(formats)

            thumbnails = []
            media_url = media.get('media_url_https') or media.get('media_url')
            if media_url:
                def add_thumbnail(name, size):
                    thumbnails.append({
                        'id': name,
                        'url': update_url_query(media_url, {'name': name}),
                        'width': int_or_none(size.get('w') or size.get('width')),
                        'height': int_or_none(size.get('h') or size.get('height')),
                    })
                for name, size in media.get('sizes', {}).items():
                    add_thumbnail(name, size)
                add_thumbnail('orig', media.get('original_info') or {})

            info.update({
                'formats': formats,
                'thumbnails': thumbnails,
                'duration': float_or_none(video_info.get('duration_millis'), 1000),
            })

        media = try_get(status, lambda x: x['extended_entities']['media'][0])
        if media and media.get('type') != 'photo':
            extract_from_video_info(media)
        else:
            card = status.get('card')
            if card:
                binding_values = card['binding_values']

                def get_binding_value(k):
                    o = binding_values.get(k) or {}
                    return try_get(o, lambda x: x[x['type'].lower() + '_value'])

                card_name = card['name'].split(':')[-1]
                if card_name == 'player':
                    info.update({
                        '_type': 'url',
                        'url': get_binding_value('player_url'),
                    })
                elif card_name == 'periscope_broadcast':
                    info.update({
                        '_type': 'url',
                        'url': get_binding_value('url') or get_binding_value('player_url'),
                        'ie_key': PeriscopeIE.ie_key(),
                    })
                elif card_name == 'broadcast':
                    info.update({
                        '_type': 'url',
                        'url': get_binding_value('broadcast_url'),
                        'ie_key': TwitterBroadcastIE.ie_key(),
                    })
                elif card_name == 'summary':
                    info.update({
                        '_type': 'url',
                        'url': get_binding_value('card_url'),
                    })
                elif card_name == 'unified_card':
                    media_entities = self._parse_json(get_binding_value('unified_card'), twid)['media_entities']
                    extract_from_video_info(next(iter(media_entities.values())))
                # amplify, promo_video_website, promo_video_convo, appplayer,
                # video_direct_message, poll2choice_video, poll3choice_video,
                # poll4choice_video, ...
                else:
                    is_amplify = card_name == 'amplify'
                    vmap_url = get_binding_value('amplify_url_vmap') if is_amplify else get_binding_value('player_stream_url')
                    content_id = get_binding_value('%s_content_id' % (card_name if is_amplify else 'player'))
                    formats = self._extract_formats_from_vmap_url(vmap_url, content_id or twid)
                    self._sort_formats(formats)

                    thumbnails = []
                    for suffix in ('_small', '', '_large', '_x_large', '_original'):
                        image = get_binding_value('player_image' + suffix) or {}
                        image_url = image.get('url')
                        if not image_url or '/player-placeholder' in image_url:
                            continue
                        thumbnails.append({
                            'id': suffix[1:] if suffix else 'medium',
                            'url': image_url,
                            'width': int_or_none(image.get('width')),
                            'height': int_or_none(image.get('height')),
                        })

                    info.update({
                        'formats': formats,
                        'thumbnails': thumbnails,
                        'duration': int_or_none(get_binding_value(
                            'content_duration_seconds')),
                    })
            else:
                expanded_url = try_get(status, lambda x: x['entities']['urls'][0]['expanded_url'])
                if not expanded_url:
                    raise ExtractorError("There's no video in this tweet.")
                info.update({
                    '_type': 'url',
                    'url': expanded_url,
                })
        return info


class TwitterAmplifyIE(TwitterBaseIE):
    IE_NAME = 'twitter:amplify'
    _VALID_URL = r'https?://amp\.twimg\.com/v/(?P<id>[0-9a-f\-]{36})'

    _TEST = {
        'url': 'https://amp.twimg.com/v/0ba0c3c7-0af3-4c0a-bed5-7efd1ffa2951',
        'md5': '7df102d0b9fd7066b86f3159f8e81bf6',
        'info_dict': {
            'id': '0ba0c3c7-0af3-4c0a-bed5-7efd1ffa2951',
            'ext': 'mp4',
            'title': 'Twitter Video',
            'thumbnail': 're:^https?://.*',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        vmap_url = self._html_search_meta(
            'twitter:amplify:vmap', webpage, 'vmap url')
        formats = self._extract_formats_from_vmap_url(vmap_url, video_id)

        thumbnails = []
        thumbnail = self._html_search_meta(
            'twitter:image:src', webpage, 'thumbnail', fatal=False)

        def _find_dimension(target):
            w = int_or_none(self._html_search_meta(
                'twitter:%s:width' % target, webpage, fatal=False))
            h = int_or_none(self._html_search_meta(
                'twitter:%s:height' % target, webpage, fatal=False))
            return w, h

        if thumbnail:
            thumbnail_w, thumbnail_h = _find_dimension('image')
            thumbnails.append({
                'url': thumbnail,
                'width': thumbnail_w,
                'height': thumbnail_h,
            })

        video_w, video_h = _find_dimension('player')
        formats[0].update({
            'width': video_w,
            'height': video_h,
        })

        return {
            'id': video_id,
            'title': 'Twitter Video',
            'formats': formats,
            'thumbnails': thumbnails,
        }


class TwitterBroadcastIE(TwitterBaseIE, PeriscopeBaseIE):
    IE_NAME = 'twitter:broadcast'
    _VALID_URL = TwitterBaseIE._BASE_REGEX + r'i/broadcasts/(?P<id>[0-9a-zA-Z]{13})'

    _TEST = {
        # untitled Periscope video
        'url': 'https://twitter.com/i/broadcasts/1yNGaQLWpejGj',
        'info_dict': {
            'id': '1yNGaQLWpejGj',
            'ext': 'mp4',
            'title': 'Andrea May Sahouri - Periscope Broadcast',
            'uploader': 'Andrea May Sahouri',
            'uploader_id': '1PXEdBZWpGwKe',
        },
    }

    def _real_extract(self, url):
        broadcast_id = self._match_id(url)
        broadcast = self._call_api(
            'broadcasts/show.json', broadcast_id,
            {'ids': broadcast_id})['broadcasts'][broadcast_id]
        info = self._parse_broadcast_data(broadcast, broadcast_id)
        media_key = broadcast['media_key']
        source = self._call_api(
            'live_video_stream/status/' + media_key, media_key)['source']
        m3u8_url = source.get('noRedirectPlaybackUrl') or source['location']
        if '/live_video_stream/geoblocked/' in m3u8_url:
            self.raise_geo_restricted()
        m3u8_id = compat_parse_qs(compat_urllib_parse_urlparse(
            m3u8_url).query).get('type', [None])[0]
        state, width, height = self._extract_common_format_info(broadcast)
        info['formats'] = self._extract_pscp_m3u8_formats(
            m3u8_url, broadcast_id, m3u8_id, state, width, height)
        return info


class TwitterShortenerIE(TwitterBaseIE):
    IE_NAME = 'twitter:shortener'
    _VALID_URL = r'https?://t.co/(?P<id>[^?]+)|tco:(?P<eid>[^?]+)'
    _BASE_URL = 'https://t.co/'

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        eid, id = mobj.group('eid', 'id')
        if eid:
            id = eid
            url = self._BASE_URL + id
        new_url = self._request_webpage(url, id, headers={'User-Agent': 'curl'}).geturl()
        __UNSAFE_LINK = "https://twitter.com/safety/unsafe_link_warning?unsafe_link="
        if new_url.startswith(__UNSAFE_LINK):
            new_url = new_url.replace(__UNSAFE_LINK, "")
        return self.url_result(new_url)
