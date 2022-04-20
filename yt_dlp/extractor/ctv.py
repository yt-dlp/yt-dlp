from .common import InfoExtractor


class CTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ctv\.ca/(?P<id>(?:show|movie)s/[^/]+/[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.ctv.ca/shows/your-morning/wednesday-december-23-2020-s5e88',
        'info_dict': {
            'id': '2102249',
            'ext': 'flv',
            'title': 'Wednesday, December 23, 2020',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'Your Morning delivers original perspectives and unique insights into the headlines of the day.',
            'timestamp': 1608732000,
            'upload_date': '20201223',
            'series': 'Your Morning',
            'season': '2020-2021',
            'season_number': 5,
            'episode_number': 88,
            'tags': ['Your Morning'],
            'categories': ['Talk Show'],
            'duration': 7467.126,
        },
    }, {
        'url': 'https://www.ctv.ca/movies/adam-sandlers-eight-crazy-nights/adam-sandlers-eight-crazy-nights',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        content = self._download_json(
            'https://www.ctv.ca/space-graphql/graphql', display_id, query={
                'query': '''{
  resolvedPath(path: "/%s") {
    lastSegment {
      content {
        ... on AxisContent {
          axisId
          videoPlayerDestCode
        }
      }
    }
  }
}''' % display_id,
            })['data']['resolvedPath']['lastSegment']['content']
        video_id = content['axisId']
        return self.url_result(
            '9c9media:%s:%s' % (content['videoPlayerDestCode'], video_id),
            'NineCNineMedia', video_id)
