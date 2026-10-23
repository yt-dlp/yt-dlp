#!/usr/bin/env python3

import json
import unittest
from unittest.mock import patch

from test.helper import FakeYDL
from yt_dlp.extractor.facebook import FacebookIE


class TestFacebookMetrics(unittest.TestCase):
    VIDEO_ID = '585113017885063'

    def setUp(self):
        self.ie = FacebookIE(FakeYDL())

    def webpage(self, data=None, title=None, canonical=None):
        return ''.join((
            f'<meta property="og:url" content="https://www.facebook.com/reel/{canonical or self.VIDEO_ID}">',
            f'<meta property="og:title" content="{title}">' if title else '',
            f'<script type="application/json" data-sjs>{json.dumps(data)}</script>' if data is not None else '',
        ))

    def metrics(self, data=None, title=None, info=None, canonical=None):
        return self.ie._extract_video_metrics(
            self.webpage(data, title, canonical), self.VIDEO_ID, info or {})

    def test_statistics_prefixes(self):
        # Reduced prefixes from public responses captured on 2026-10-23.
        for title, reactions, comments in (
            ('92 reactions · 152 comments | Video', 92, 152),
            ('65 reactions · 85 comments | Video', 65, 85),
            ('1.2K views · 56 reactions | Video', 56, None),
            ('1.1K views · 90 reactions | Video', 90, None),
        ):
            with self.subTest(title=title):
                info = self.metrics(title=title)
                self.assertEqual(info.get('reaction_count'), reactions)
                self.assertEqual(info.get('like_count'), reactions)
                self.assertEqual(info.get('like_metric'), 'reactions')
                self.assertEqual(info.get('comment_count'), comments)

    def test_structured_feedback(self):
        # Selected fields from a real data-sjs response; no media/session data.
        info = self.metrics({
            'id': self.VIDEO_ID,
            'feedback': {
                'reaction_count': {'count': 90},
                'total_comment_count': 111,
                'video_view_count_renderer': {'feedback': {
                    'associated_video': {'id': self.VIDEO_ID},
                    'video_view_count': 584,
                    'play_count': 1131,
                    'play_count_reduced': '1.1K',
                }},
                'top_reactions': {'edges': [{'reaction_count': 58}, {'reaction_count': 27}]},
            },
        }, title='1.1K views · 89 reactions · 110 comments | Video')
        self.assertEqual(info['view_count'], 584)
        self.assertEqual(info['reaction_count'], 90)
        self.assertEqual(info['like_count'], 90)
        self.assertEqual(info['comment_count'], 111)
        self.assertEqual(info['facebook_metrics']['video_id'], self.VIDEO_ID)
        self.assertIn('reaction_count.count', info['facebook_metrics']['sources']['reaction_count'])

    def test_recommendations_and_unassociated_feedback(self):
        info = self.metrics({
            'recommended': {'id': '999999999', 'feedback': {
                'reaction_count': {'count': 999}, 'total_comment_count': 999, 'video_view_count': 999,
            }},
            'unrelated': {'feedback': {'reaction_count': {'count': 888}, 'video_view_count': 888}},
            'target': {'id': self.VIDEO_ID, 'feedback': {'total_comment_count': 85}},
        })
        self.assertEqual(info['comment_count'], 85)
        self.assertIsNone(info.get('reaction_count'))
        self.assertIsNone(info.get('view_count'))

    def test_associated_video(self):
        info = self.metrics({'feedback': {
            'associated_video': {'id': self.VIDEO_ID},
            'reaction_count': {'count': 65},
            'comment_rendering_instance': {'comments': {'total_count': 85}},
        }})
        self.assertEqual(info['reaction_count'], 65)
        self.assertEqual(info['comment_count'], 85)

    def test_feedback_url_identity(self):
        info = self.metrics({'posts': [
            {'url': f'https://www.facebook.com/watch/?v={self.VIDEO_ID}9',
             'feedback': {'likers': {'count': 999}, 'total_comment_count': 999}},
            {'url': f'https://www.facebook.com/watch/?v={self.VIDEO_ID}',
             'feedback': {'likers': {'count': 0}, 'total_comment_count': 85}},
        ]})
        self.assertEqual(info['like_count'], 0)
        self.assertEqual(info['like_metric'], 'likes')
        self.assertEqual(info['comment_count'], 85)

    def test_conflicting_association(self):
        info = self.metrics({'id': self.VIDEO_ID, 'feedback': {
            'associated_video': {'id': '999999999'},
            'reaction_count': {'count': 999},
            'video_view_count_renderer': {'feedback': {'video_view_count': 999}},
        }})
        self.assertIsNone(info.get('reaction_count'))
        self.assertIsNone(info.get('view_count'))
        info = self.metrics({'id': self.VIDEO_ID, 'feedback': {
            'video_view_count_renderer': {'feedback': {
                'associated_video': {'id': '999999999'}, 'video_view_count': 999,
            }},
        }})
        self.assertIsNone(info.get('view_count'))

    def test_zero_and_missing(self):
        info = self.metrics(title='1,234 views · 0 reactions · 0 comments | Video')
        self.assertEqual(info['view_count'], 1234)
        self.assertEqual(info['like_count'], 0)
        self.assertEqual(info['comment_count'], 0)
        self.assertEqual(self.metrics()['facebook_metrics']['missing_reasons']['comment_count'], 'not_returned')
        for value in (True, -1, 1.5, '1.5K'):
            with self.subTest(value=value):
                info = self.metrics({'id': self.VIDEO_ID, 'feedback': {'total_comment_count': value}})
                self.assertIsNone(info.get('comment_count'))

    def test_structured_zero_and_reaction_total(self):
        info = self.metrics({'id': self.VIDEO_ID, 'creation_story': {'feedback': {
            'reaction_count': 0, 'total_comment_count': 0, 'video_view_count': 0,
        }}})
        for field in ('view_count', 'like_count', 'reaction_count', 'comment_count'):
            self.assertEqual(info[field], 0)

    def test_canonical_title_fallback(self):
        info = self.ie._extract_video_metrics(
            f'<link rel="canonical" href="https://www.facebook.com/watch/?v={self.VIDEO_ID}">'
            '<title>1&#8239;234 views &#183; 92 reactions &#183; 152 comments | Video</title>',
            self.VIDEO_ID, {})
        self.assertEqual(info['view_count'], 1234)
        self.assertEqual(info['reaction_count'], 92)
        self.assertEqual(info['comment_count'], 152)

    def test_approximate_counts(self):
        info = self.metrics(title='1.1K views · 2万 reactions · 1.2K comments | Video')
        for field in ('view_count', 'reaction_count', 'like_count', 'comment_count'):
            self.assertIsNone(info.get(field))
        self.assertEqual(info['facebook_metrics']['approximate']['view_count'], '1.1K')
        self.assertEqual(info['facebook_metrics']['missing_reasons']['comment_count'], 'approximate_only')

    def test_existing_exact_counts(self):
        info = self.metrics({'id': self.VIDEO_ID, 'feedback': {
            'video_view_count': 584, 'total_comment_count': 111,
        }}, title='1.1K views · 90 reactions · 110 comments | Video', info={
            'view_count': 600, 'comment_count': 0,
        })
        self.assertEqual(info['view_count'], 600)
        self.assertEqual(info['comment_count'], 0)

    def test_metadata_identity_and_body_numbers(self):
        info = self.metrics(title='99 reactions · 999 comments | Other video', canonical='999999999')
        self.assertIsNone(info.get('reaction_count'))
        for title in ('I got 50 comments today | 10 reactions', 'Sale 30% off · 20 comments'):
            with self.subTest(title=title):
                self.assertIsNone(self.metrics(title=title).get('comment_count'))
        info = self.metrics(title='1,234次观看 &#183; 0个心情 &#183; 0条评论 | Video')
        self.assertEqual(info['view_count'], 1234)
        self.assertEqual(info['reaction_count'], 0)
        self.assertEqual(info['comment_count'], 0)

    def test_login_reason(self):
        for html, reason in (
            ('<p>You must log in to continue.</p>', 'login_required'),
            ('<button>Log in</button>', 'not_returned'),
            ('<script>"You must log in to continue"</script>', 'not_returned'),
        ):
            with self.subTest(html=html):
                info = self.ie._extract_video_metrics(html, self.VIDEO_ID, {})
                self.assertEqual(info['facebook_metrics']['missing_reasons']['view_count'], reason)

    def test_extractor_integration(self):
        video = {'id': self.VIDEO_ID, '__typename': 'Video',
                 'playable_url': 'https://example.com/video.mp4',
                 'feedback': {'reaction_count': {'count': 90}, 'total_comment_count': 111,
                              'video_view_count': 584}}
        webpage = self.webpage({'require': [[
            'RelayPrefetchedStreamCache', None, [], [{'__bbox': {'result': {'data': {'video': video}}}}],
        ]]}, title='1.1K views · 90 reactions | Video')
        with patch.object(self.ie, '_download_webpage', return_value=webpage) as download:
            info = self.ie._extract_from_url(f'https://www.facebook.com/watch/?v={self.VIDEO_ID}', self.VIDEO_ID)
        self.assertEqual(info['id'], self.VIDEO_ID)
        self.assertEqual(info['view_count'], 584)
        self.assertEqual(info['like_count'], 90)
        self.assertEqual(info['comment_count'], 111)
        download.assert_called_once()


if __name__ == '__main__':
    unittest.main()
