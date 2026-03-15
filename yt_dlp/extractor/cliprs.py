from .common import InfoExtractor


class ClipRsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?clip\.rs/(?P<id>[^/]+)/\d+'
    _TEST = {{
        'url': 'https://www.clip.rs/premijera-4-ruze-okupila-poznate-glumica-u-prekratkoj-haljini-branka-i-gagi-ne-skidaju-osmeh-a-kubura-bez-zene-video/15231',  # 'rasrs-blic.pulsevideo.eu format"
        'info_dict': {
            'id': '2156960.1306067903',
            'display_id': 'premijera-4-ruze-okupila-poznate-glumica-u-prekratkoj-haljini-branka-i-gagi-ne-skidaju-osmeh-a-kubura-bez-zene-video',
            'ext': 'mp4',
            'title': 'PREMIJERA "4 RUŽE" OKUPILA POZNATE Glumica u PREKRATKOJ HALJINI, Branka i Gagi ne skidaju osmeh, a Kubura BEZ ŽENE (VIDEO)',
        },
    }, {
        'url': 'https://www.clip.rs/ceca-otputovala-sa-deckom-i-njegovom-cerkom-evo-gde-su-otisli-uzivace-zajedno-u-zimskoj-idili/15690',  # 'rasrs-blic.embed.videos.ringpublishing.com' format
        'info_dict': {
            'id': '2212947.809338313',
            'display_id': 'ceca-otputovala-sa-deckom-i-njegovom-cerkom-evo-gde-su-otisli-uzivace-zajedno-u-zimskoj-idili',
            'ext': 'mp4',
            'title': 'Ceca otputovala sa DEČKOM I NJEGOVOM ĆERKOM! Evo gde su otišli, uživaće zajedno u zimskoj idili',
        },

    }}

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        video_id = None
        display_id = None
        video_url = None
        title = self._og_search_title(webpage)

        return {
            'id': video_id,
            'display_id': display_id,
            'url': video_url,
            'title': title,
        }
