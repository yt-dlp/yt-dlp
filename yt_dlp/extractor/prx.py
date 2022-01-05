# coding: utf-8
from __future__ import unicode_literals

import itertools
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    GeoRestrictedError,
    orderedSet,
    unified_strdate,
    urlencode_postdata,
    urljoin,
    traverse_obj,
    int_or_none,
    mimetype2ext,
    clean_html,
    url_or_none,
    parse_dfxp_time_expr,
get_domain
)

import typing

class PRXBaseIE(InfoExtractor):
    PRX_BASE_URL_RE = r'https?://(?:beta\.)?prx.org/'

    def _call_api(self, item_id, path, query=None, fatal=True, note='Downloading CMS API JSON'):
        return self._download_json(
            urljoin('https://cms.prx.org/api/v1/', path), item_id, query=query, fatal=fatal)

    @staticmethod
    def _extract_embedded_data(response):
        return traverse_obj(response, '_embedded', expected_type=dict, default={})

    @classmethod
    def _get_prx_embed_response(cls, response, section):
        return cls._extract_embedded_data(response).get(f'prx:{section}')

    @staticmethod
    def _extract_file_link(response):
        return url_or_none(traverse_obj(
            response, ('_links', 'enclosure', 'href'), expected_type=str))

    def _extract_account(self, account_response):
        pass

    @classmethod
    def _extract_image(cls, image_response):
        if not isinstance(image_response, dict):
            return
        return {
            'id': str(image_response.get('id')),
            'filesize': image_response.get('size'),
            'width': image_response.get('width'),
            'height': image_response.get('height'),
            'url':  cls._extract_file_link(image_response)
        }

    @classmethod
    def _extract_series(cls, series_response):
        if not isinstance(series_response, dict):
            return
        series_id = str(series_response.get('id'))
        title = series_response.get('title')
        if not series_id or not title:
            return
        thumbnail_dict = cls._extract_image(cls._get_prx_embed_response(series_response, 'image'))
        return {
            'id': series_id,
            'title': title,
            'description': series_response.get('shortDescription'),
            'thumbnails': [thumbnail_dict] if thumbnail_dict else None
        }


class PRXStoryBaseIE(PRXBaseIE):

    # This extract type Audio (the literal audio format)
    # TODO: there is also audio-versions type, which includes Audio types.
    #  But it may include things such as transcript?

    def _extract_audio_pieces(self, audio_response):
        # TODO: concatenate the pieces with a concat PP is implemented
        # Currently returning as multi_video for the time being
        pieces = []
        piece_response = self._get_prx_embed_response(audio_response, 'items') or []
        piece_response.sort(key=lambda x: int_or_none(x.get('position')))
        for piece_response in self._get_prx_embed_response(audio_response, 'items'):
            pieces.append({
                'format_id': str(piece_response.get('id')),
                'filesize': int_or_none(piece_response.get('size')),
                'duration': int_or_none(piece_response.get('duration')),
                'ext': mimetype2ext(piece_response.get('contentType')),
                'asr': int_or_none(piece_response.get('frequency'), scale=1000),
                'abr': int_or_none(piece_response.get('bitRate')),
                'url': self._extract_file_link(piece_response),
                'vcodec': 'none',
            })
        return pieces

    def _extract_story(self, story_response):
        if not isinstance(story_response, dict):
            return
        story_id = str(story_response.get('id'))
        title = story_response.get('title')
        if not story_id or not title:
            return

        # TODO: there is also mdDescription (markdown description). Might only be set when 'description' is avail.
        description = clean_html(story_response.get('description')) or story_response.get('shortDescription')

        # TODO: uploader/account details
        series = self._extract_series(
            self._get_prx_embed_response(story_response, 'series')) or {}

        main_info = {
            'title': title,
            'description': description,
            'duration': int_or_none(story_response.get('duration')),
            'tags': story_response.get('tags'),
            'release_date': unified_strdate(story_response.get('producedOn')),
            'series': series.get('title'),
            'series_id': series.get('id'),
        }
        entries = []
        audio_pieces = self._extract_audio_pieces(
            self._get_prx_embed_response(story_response, 'audio'))
        for idx, fmt in enumerate(audio_pieces):
            entries.append({
                '_type': 'video',
                'id': '%s_part%d' % (story_id, (idx + 1)),
                'formats': [fmt],
                **main_info
            })

        return {
            '_type': 'multi_video',
            'id': story_id,
            'entries': entries,
            **main_info
        }


class PRXStoryIE(PRXStoryBaseIE):
    _VALID_URL = PRXBaseIE.PRX_BASE_URL_RE + r'stories/(?P<id>\d+)'

    def _real_extract(self, url):
        story_id = self._match_id(url)
        response = self._call_api(story_id, f'stories/{story_id}')
        story = self._extract_story(response)
        return story


class PRXSeriesIE(PRXStoryBaseIE):
    _VALID_URL = PRXBaseIE.PRX_BASE_URL_RE + r'series/(?P<id>\d+)'

    def _entries(self, series_id, url):
        total = 0
        for page in itertools.count(1):
            response = self._call_api(
                f'{series_id}: page {page}', f'series/{series_id}/stories', query={'page': page})
            for story_response in self._get_prx_embed_response(response, 'items') or []:
                story = self._extract_story(story_response)
                if story:
                    if story.get('entries'):
                        # The series API already gave us all the information needed to download the stories
                        story.update({
                            'webpage_url': f'https://{get_domain(url)}/story/{story["id"]}',
                            'extractor_key': PRXStoryIE.ie_key(),
                            'extractor': PRXStoryIE.ie_key()
                        })
                    yield story
                total += 1
            if not response or total >= response.get('total'):
                break

    def _real_extract(self, url):
        series_id = self._match_id(url)
        response = self._call_api(series_id, f'series/{series_id}')
        return {
            '_type': 'playlist',
            'entries': self._entries(series_id, url),
            **self._extract_series(response)
        }




