from .nuevo import NuevoBaseIE


class LoveHomePornIE(NuevoBaseIE):
    _VALID_URL = r'https?://(?:www\.)?lovehomeporn\.com/video/(?P<id>\d+)(?:/(?P<display_id>[^/?#&]+))?'
    _TEST = {
        'url': 'http://lovehomeporn.com/video/48483/stunning-busty-brunette-girlfriend-sucking-and-riding-a-big-dick#menu',
        'info_dict': {
            'id': '48483',
            'display_id': 'stunning-busty-brunette-girlfriend-sucking-and-riding-a-big-dick',
            'ext': 'mp4',
            'title': 'Stunning busty brunette girlfriend sucking and riding a big dick',
            'age_limit': 18,
            'duration': 238.47,
        },
        'params': {
            'skip_download': True,
        }
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        display_id = mobj.group('display_id')

        info = self._extract_nuevo(
            'http://lovehomeporn.com/media/nuevo/config.php?key=%s' % video_id,
            video_id)
        info.update({
            'display_id': display_id,
            'age_limit': 18
        })
        return info
