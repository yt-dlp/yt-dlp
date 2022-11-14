import re

from .theplatform import ThePlatformIE
from ..utils import (
    int_or_none,
    parse_age_limit,
    try_get,
    update_url_query,
)


class AMCNetworksIE(ThePlatformIE):
    _VALID_URL = r'https?://(?:www\.)?(?P<site>amc|bbcamerica|ifc|(?:we|sundance)tv)\.com/(?P<id>(?:movies|shows(?:/[^/]+)+)/[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.bbcamerica.com/shows/the-graham-norton-show/videos/tina-feys-adorable-airline-themed-family-dinner--51631',
        'info_dict': {
            'id': '4Lq1dzOnZGt0',
            'ext': 'mp4',
            'title': "The Graham Norton Show - Season 28 - Tina Fey's Adorable Airline-Themed Family Dinner",
            'description': "It turns out child stewardesses are very generous with the wine! All-new episodes of 'The Graham Norton Show' premiere Fridays at 11/10c on BBC America.",
            'upload_date': '20201120',
            'timestamp': 1605904350,
            'uploader': 'AMCN',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://www.bbcamerica.com/shows/the-hunt/full-episodes/season-1/episode-01-the-hardest-challenge',
        'only_matching': True,
    }, {
        'url': 'http://www.amc.com/shows/preacher/full-episodes/season-01/episode-00/pilot',
        'only_matching': True,
    }, {
        'url': 'http://www.wetv.com/shows/million-dollar-matchmaker/season-01/episode-06-the-dumped-dj-and-shallow-hal',
        'only_matching': True,
    }, {
        'url': 'http://www.ifc.com/movies/chaos',
        'only_matching': True,
    }, {
        'url': 'http://www.bbcamerica.com/shows/doctor-who/full-episodes/the-power-of-the-daleks/episode-01-episode-1-color-version',
        'only_matching': True,
    }, {
        'url': 'http://www.wetv.com/shows/mama-june-from-not-to-hot/full-episode/season-01/thin-tervention',
        'only_matching': True,
    }, {
        'url': 'http://www.wetv.com/shows/la-hair/videos/season-05/episode-09-episode-9-2/episode-9-sneak-peek-3',
        'only_matching': True,
    }, {
        'url': 'https://www.sundancetv.com/shows/riviera/full-episodes/season-1/episode-01-episode-1',
        'only_matching': True,
    }]
    _REQUESTOR_ID_MAP = {
        'amc': 'AMC',
        'bbcamerica': 'BBCA',
        'ifc': 'IFC',
        'sundancetv': 'SUNDANCE',
        'wetv': 'WETV',
    }

    def _real_extract(self, url):
        site, display_id = self._match_valid_url(url).groups()
        requestor_id = self._REQUESTOR_ID_MAP[site]
        page_data = self._download_json(
            'https://content-delivery-gw.svc.ds.amcn.com/api/v2/content/amcn/%s/url/%s'
            % (requestor_id.lower(), display_id), display_id)['data']
        properties = page_data.get('properties') or {}
        query = {
            'mbr': 'true',
            'manifest': 'm3u',
        }

        video_player_count = 0
        try:
            for v in page_data['children']:
                if v.get('type') == 'video-player':
                    releasePid = v['properties']['currentVideo']['meta']['releasePid']
                    tp_path = 'M_UwQC/' + releasePid
                    media_url = 'https://link.theplatform.com/s/' + tp_path
                    video_player_count += 1
        except KeyError:
            pass
        if video_player_count > 1:
            self.report_warning(
                'The JSON data has %d video players. Only one will be extracted' % video_player_count)

        # Fall back to videoPid if releasePid not found.
        # TODO: Fall back to videoPid if releasePid manifest uses DRM.
        if not video_player_count:
            tp_path = 'M_UwQC/media/' + properties['videoPid']
            media_url = 'https://link.theplatform.com/s/' + tp_path

        theplatform_metadata = self._download_theplatform_metadata(tp_path, display_id)
        info = self._parse_theplatform_metadata(theplatform_metadata)
        video_id = theplatform_metadata['pid']
        title = theplatform_metadata['title']
        rating = try_get(
            theplatform_metadata, lambda x: x['ratings'][0]['rating'])
        video_category = properties.get('videoCategory')
        if video_category and video_category.endswith('-Auth'):
            resource = self._get_mvpd_resource(
                requestor_id, title, video_id, rating)
            query['auth'] = self._extract_mvpd_auth(
                url, video_id, requestor_id, resource)
        media_url = update_url_query(media_url, query)
        formats, subtitles = self._extract_theplatform_smil(
            media_url, video_id)
        self._sort_formats(formats)

        thumbnails = []
        thumbnail_urls = [properties.get('imageDesktop')]
        if 'thumbnail' in info:
            thumbnail_urls.append(info.pop('thumbnail'))
        for thumbnail_url in thumbnail_urls:
            if not thumbnail_url:
                continue
            mobj = re.search(r'(\d+)x(\d+)', thumbnail_url)
            thumbnails.append({
                'url': thumbnail_url,
                'width': int(mobj.group(1)) if mobj else None,
                'height': int(mobj.group(2)) if mobj else None,
            })

        info.update({
            'age_limit': parse_age_limit(rating),
            'formats': formats,
            'id': video_id,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
        })
        ns_keys = theplatform_metadata.get('$xmlns', {}).keys()
        if ns_keys:
            ns = list(ns_keys)[0]
            episode = theplatform_metadata.get(ns + '$episodeTitle') or None
            episode_number = int_or_none(
                theplatform_metadata.get(ns + '$episode'))
            season_number = int_or_none(
                theplatform_metadata.get(ns + '$season'))
            series = theplatform_metadata.get(ns + '$show') or None
            info.update({
                'episode': episode,
                'episode_number': episode_number,
                'season_number': season_number,
                'series': series,
            })
        return info
