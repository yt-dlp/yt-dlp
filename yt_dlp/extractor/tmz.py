# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    get_element_by_attribute,
)


class TMZIE(InfoExtractor):
    _VALID_URL = r"https?://(?:www\.)?tmz\.com/.*"
    _TESTS = [
        {
            "url": "http://www.tmz.com/videos/0-cegprt2p/",
            "info_dict": {
                "id": "http://www.tmz.com/videos/0-cegprt2p/",
                "ext": "mp4",
                "title": "No Charges Against Hillary Clinton? Harvey Says It Ain't Over Yet",
                "description": "Harvey talks about Director Comey’s decision not to prosecute Hillary Clinton.",
                "timestamp": 1467831837,
                "uploader": "{'@type': 'Person', 'name': 'TMZ Staff'}",
                "upload_date": "20160706",
            },
        },
        {
            "url": "https://www.tmz.com/videos/071119-chris-morgan-women-4590005-0-zcsejvcr/",
            "info_dict": {
                "id": "https://www.tmz.com/videos/071119-chris-morgan-women-4590005-0-zcsejvcr/",
                "ext": "mp4",
                "title": "Angry Bagel Shop Guy Says He Doesn't Trust Women",
                "description": "The enraged man who went viral for ranting about women on dating sites before getting ragdolled in a bagel shop is defending his misogyny ... he says it's women's fault in the first place.",
                "timestamp": 1562889485,
                "uploader": "{'@type': 'Person', 'name': 'TMZ Staff'}",
                "upload_date": "20190711",
            },
        },
        {
            "url": "http://www.tmz.com/2015/04/19/bobby-brown-bobbi-kristina-awake-video-concert",
            "md5": "5429c85db8bde39a473a56ca8c4c5602",
            "info_dict": {
                "id": "http://www.tmz.com/2015/04/19/bobby-brown-bobbi-kristina-awake-video-concert",
                "ext": "mp4",
                "title": "Bobby Brown Tells Crowd ... Bobbi Kristina is Awake",
                "description": 'Bobby Brown stunned his audience during a concert Saturday night, when he told the crowd, "Bobbi is awake.  She\'s watching me."',
                "timestamp": 1429467813,
                "uploader": "{'@type': 'Person', 'name': 'TMZ Staff'}",
                "upload_date": "20150419",
            },
        },
        {
            "url": "http://www.tmz.com/2015/09/19/patti-labelle-concert-fan-stripping-kicked-out-nicki-minaj/",
            "info_dict": {
                "id": "http://www.tmz.com/2015/09/19/patti-labelle-concert-fan-stripping-kicked-out-nicki-minaj/",
                "ext": "mp4",
                "title": "Patti LaBelle -- Goes Nuclear On Stripping Fan",
                "description": "Patti LaBelle made it known loud and clear last night ... NO "
                "ONE gets on her stage and strips down.",
                "timestamp": 1442683746,
                "uploader": "{'@type': 'Person', 'name': 'TMZ Staff'}",
                "upload_date": "20150919",
            },
        },
        {
            "url": "http://www.tmz.com/2016/01/28/adam-silver-sting-drake-blake-griffin/",
            "info_dict": {
                "id": "http://www.tmz.com/2016/01/28/adam-silver-sting-drake-blake-griffin/",
                "ext": "mp4",
                "title": "NBA's Adam Silver -- Blake Griffin's a Great Guy ... He'll Learn from This",
                "description": "Two pretty parts of this video with NBA Commish Adam Silver.",
                "timestamp": 1454010989,
                "uploader": "{'@type': 'Person', 'name': 'TMZ Staff'}",
                "upload_date": "20160128",
            },
        },
        {
            "url": "http://www.tmz.com/2016/10/27/donald-trump-star-vandal-arrested-james-otis/",
            "info_dict": {
                "id": "http://www.tmz.com/2016/10/27/donald-trump-star-vandal-arrested-james-otis/",
                "ext": "mp4",
                "title": "Trump Star Vandal -- I'm Not Afraid of Donald or the Cops!",
                "description": "James Otis is the the guy who took a pickaxe to Donald Trump's star on the Walk of Fame, and he tells TMZ .. he's ready and willing to go to jail for the crime.",
                "timestamp": 1477500095,
                "uploader": "{'@type': 'Person', 'name': 'TMZ Staff'}",
                "upload_date": "20161026",
            },
        },
        {
            "url": "https://www.tmz.com/videos/2020-10-31-103120-beverly-hills-protest-4878209/",
            "info_dict": {
                "id": "https://www.tmz.com/videos/2020-10-31-103120-beverly-hills-protest-4878209/",
                "ext": "mp4",
                "title": "Cops Use Billy Clubs Against Pro-Trump and Anti-Fascist "
                "Demonstrators",
                "description": "Beverly Hills may be an omen of what's coming next week, "
                "because things got crazy on the streets and cops started "
                "swinging their billy clubs at both Anti-Fascist and Pro-Trump "
                "demonstrators.",
                "timestamp": 1604182772,
                "uploader": "{'@type': 'Person', 'name': 'TMZ Staff'}",
                "upload_date": "20201031",
            },
        },
        {
            "url": "https://www.tmz.com/2020/11/05/gervonta-davis-car-crash-hit-and-run-police/",
            "info_dict": {
                "id": "Dddb6IGe-ws",
                "ext": "mp4",
                "title": "SICK LAMBO GERVONTA DAVIS IN HIS NEW RIDE RIGHT AFTER KO AFTER LEO  EsNews Boxing",
                "uploader": "ESNEWS",
                "description": "md5:49675bc58883ccf80474b8aa701e1064",
                "upload_date": "20201101",
                "uploader_id": "ESNEWS",
            },
        },
        {
            "url": "https://www.tmz.com/2020/11/19/conor-mcgregor-dustin-poirier-contract-fight-ufc-257-fight-island/",
            "info_dict": {
                "id": "1329450007125225473",
                "ext": "mp4",
                "title": "TheMacLife - BREAKING: Conor McGregor (@thenotoriousmma) has signed his bout agreement for his rematch with Dustin Poirier for January 23.",
                "uploader": "TheMacLife",
                "description": "md5:56e6009bbc3d12498e10d08a8e1f1c69",
                "upload_date": "20201119",
                "uploader_id": "Maclifeofficial",
                "timestamp": 1605800556,
            },
        },
    ]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, url)
        jsonld = self._search_json_ld(webpage, url)
        if not jsonld or "url" not in jsonld:
            # try to extract from YouTube Player API
            # see https://developers.google.com/youtube/iframe_api_reference#Video_Queueing_Functions
            match_obj = re.search(r'\.cueVideoById\(\s*(?P<quote>[\'"])(?P<id>.*?)(?P=quote)', webpage)
            if match_obj:
                res = self.url_result(match_obj.group("id"))
                return res
            # try to extract from twitter
            blockquote_el = get_element_by_attribute("class", "twitter-tweet", webpage)
            if blockquote_el:
                matches = re.findall(
                    r'<a[^>]+href=\s*(?P<quote>[\'"])(?P<link>.*?)(?P=quote)',
                    blockquote_el)
                if matches:
                    for _, match in matches:
                        if "/status/" in match:
                            res = self.url_result(match)
                            return res
            raise ExtractorError("No video found!")
        if id not in jsonld:
            jsonld["id"] = url
        return jsonld
