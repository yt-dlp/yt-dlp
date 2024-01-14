
from .common import InfoExtractor


class IlPostExtractorIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ilpost\.it/episodes/(?P<id>[^/?]+).*'
    _TESTS = [{
        'url': 'https://www.ilpost.it/episodes/1-avis-akvasas-ka/',
        'md5': '43649f002d85e1c2f319bb478d479c40',
        'info_dict': {
            'id': '2972047',
            'ext': 'mp3',
            'display_id': '1-avis-akvasas-ka',
            'title': '1. Avis akvasas ka',
            'url': 'https://www.ilpost.it/wp-content/uploads/2023/12/28/1703781217-l-invasione-pt1-v6.mp3',
            'timestamp': 1703835014,
            'upload_date': '20231229',
            'duration': 2495.0,
            'availability': 'public',
            'media_type': 'episode',
            'series_id': '235598',
            'episode_number': 1,
            'episode': 'Episode 1',
            # Then if the test run fails, it will output the missing/incorrect fields.
            # Properties can be added as:
            # * A value, e.g.
            #     'title': 'Video title goes here',
            # * MD5 checksum; start the string with 'md5:', e.g.
            #     'description': 'md5:098f6bcd4621d373cade4e832627b4f6',
            # * A regular expression; start the string with 're:', e.g.
            #     'thumbnail': r're:^https?://.*\.jpg$',
            # * A count of elements in a list; start the string with 'count:', e.g.
            #     'tags': 'count:10',
            # * Any Python type, e.g.
            #     'view_count': int,
        }
    }]

    def _real_extract(self, url):
        podcast_display_id = self._match_id(url)
        webpage = self._download_webpage(url, podcast_display_id)

        endpoint_metadata = self._search_json(start_pattern='var ilpostpodcast = ', end_pattern=';', string=webpage, name='endpoint-metadata', video_id=podcast_display_id)
        endpoint_url = endpoint_metadata["ajax_url"]
        ajax_cookie = endpoint_metadata["cookie"]
        episode_id = endpoint_metadata["post_id"]
        podcast_id = endpoint_metadata["podcast_id"]
        # We don't need escaping because all values are POST-safe
        post_data = f"action=checkpodcast&cookie={ajax_cookie}&post_id={episode_id}&podcast_id={podcast_id}"
        podcast_metadata = self._download_json(endpoint_url, podcast_display_id, data=str.encode(post_data))
        episodes = podcast_metadata["data"]["postcastList"]

        for idx, episode in enumerate(episodes):
            if str(episode["id"]) == episode_id:
                ret = {
                    'id': episode_id,
                    'display_id': podcast_display_id,
                    'title': episode["title"],
                    'url': episode["podcast_raw_url"],
                    'timestamp': episode["timestamp"],
                    'duration': episode["milliseconds"] / 1000,
                    'availability': self._availability(needs_premium=not episode["free"], is_private=False, needs_subscription=False, needs_auth=False, is_unlisted=False),
                    'media_type': episode['object'],

                    'series_id': podcast_id,
                    'episode_number': idx + 1,
                }
                if episode["description"]:
                    ret["description"] = episode["description"]
                if episode["image"]:
                    ret["thumbnail"] = episode["image"]

                return ret
        return None
