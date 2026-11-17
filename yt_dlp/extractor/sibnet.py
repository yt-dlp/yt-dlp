from .common import InfoExtractor


class SibnetEmbedIE(InfoExtractor):
    # Ref: https://help.sibnet.ru/?sibnet_video_embed
    _VALID_URL = False
    _EMBED_REGEX = [r'<iframe\b[^>]+\bsrc=(["\'])(?P<url>(?:https?:)?//video\.sibnet\.ru/shell\.php\?.*?\bvideoid=\d+.*?)\1']
    _WEBPAGE_TESTS = [{
        'url': 'https://phpbb3.x-tk.ru/bbcode-video-sibnet-t24.html',
        'info_dict': {
            'id': 'shell',  # FIXME: Non unique ID?
            'ext': 'mp4',
            'age_limit': 0,
            'thumbnail': 'https://video.sibnet.ru/upload/cover/video_1887072_0.jpg',
            'title': 'КВН Москва не сразу строилась  - Девушка впервые играет в Mortal Kombat',
        },
    }]
