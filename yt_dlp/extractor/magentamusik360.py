from .common import InfoExtractor


class MagentaMusik360IE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?magenta-musik-360\.de/([a-z0-9-]+-(?P<id>[0-9]+)|festivals/.+)'
    _TESTS = [{
        'url': 'https://www.magenta-musik-360.de/within-temptation-wacken-2019-1-9208205928595185932',
        'md5': '65b6f060b40d90276ec6fb9b992c1216',
        'info_dict': {
            'id': '9208205928595185932',
            'ext': 'm3u8',
            'title': 'WITHIN TEMPTATION',
            'description': 'Robert Westerholt und Sharon Janny den Adel gründeten die Symphonic Metal-Band. Privat sind die Niederländer ein Paar und haben zwei Kinder. Die Single Ice Queen brachte ihnen Platin und Gold und verhalf 2002 zum internationalen Durchbruch. Charakteristisch für die Band war Anfangs der hohe Gesang von Frontfrau Sharon. Stilistisch fing die Band im Gothic Metal an. Mit neuem Sound, schnellen Gitarrenriffs und Gitarrensoli, avancierte Within Temptation zur erfolgreichen Rockband. Auch dieses Jahr wird die Band ihre Fangemeinde wieder mitreißen.',
        }
    }, {
        'url': 'https://www.magenta-musik-360.de/festivals/wacken-world-wide-2020-body-count-feat-ice-t',
        'md5': '81010d27d7cab3f7da0b0f681b983b7e',
        'info_dict': {
            'id': '9208205928595231363',
            'ext': 'm3u8',
            'title': 'Body Count feat. Ice-T',
            'description': 'Body Count feat. Ice-T konnten bereits im vergangenen Jahr auf dem „Holy Ground“ in Wacken überzeugen. 2020 gehen die Crossover-Metaller aus einem Club in Los Angeles auf Sendung und bringen mit ihrer Mischung aus Metal und Hip-Hop Abwechslung und ordentlich Alarm zum WWW. Bereits seit 1990 stehen die beiden Gründer Ice-T (Gesang) und Ernie C (Gitarre) auf der Bühne. Sieben Studioalben hat die Gruppe bis jetzt veröffentlicht, darunter das Debüt „Body Count“ (1992) mit dem kontroversen Track „Cop Killer“.',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        # _match_id casts to string, but since "None" is not a valid video_id for magenta
        # there is no risk for confusion
        if video_id == "None":
            webpage = self._download_webpage(url, video_id)
            video_id = self._html_search_regex(r'data-asset-id="([^"]+)"', webpage, 'video_id')
        json = self._download_json("https://wcps.t-online.de/cvss/magentamusic/vodplayer/v3/player/58935/%s/Main%%20Movie" % video_id, video_id)
        xml_url = json['content']['feature']['representations'][0]['contentPackages'][0]['media']['href']
        metadata = json['content']['feature'].get('metadata')
        title = None
        description = None
        duration = None
        thumbnails = []
        if metadata:
            title = metadata.get('title')
            description = metadata.get('fullDescription')
            duration = metadata.get('runtimeInSeconds')
            for img_key in ('teaserImageWide', 'smallCoverImage'):
                if img_key in metadata:
                    thumbnails.append({'url': metadata[img_key].get('href')})

        xml = self._download_xml(xml_url, video_id)
        final_url = xml[0][0][0].attrib['src']

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'url': final_url,
            'duration': duration,
            'thumbnails': thumbnails
        }
