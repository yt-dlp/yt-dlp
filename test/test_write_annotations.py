#!/usr/bin/env python
# coding: utf-8
from __future__ import unicode_literals

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.helper import get_params, try_rm


import io

import xml.etree.ElementTree

import yt_dlp.YoutubeDL
import yt_dlp.extractor


class YoutubeDL(yt_dlp.YoutubeDL):
    def __init__(self, *args, **kwargs):
        super(YoutubeDL, self).__init__(*args, **kwargs)
        self.to_stderr = self.to_screen


params = get_params({
    'writeannotations': True,
    'skip_download': True,
    'writeinfojson': False,
    'format': 'flv',
})


TEST_ID = 'gr51aVj-mLg'
ANNOTATIONS_FILE = TEST_ID + '.annotations.xml'
EXPECTED_ANNOTATIONS = ['Speech bubble', 'Note', 'Title', 'Spotlight', 'Label']


class TestAnnotations(unittest.TestCase):
    def setUp(self):
        # Clear old files
        self.tearDown()

    def test_info_json(self):
        expected = list(EXPECTED_ANNOTATIONS)  # Two annotations could have the same text.
        ie = yt_dlp.extractor.YoutubeIE()
        ydl = YoutubeDL(params)
        ydl.add_info_extractor(ie)
        ydl.download([TEST_ID])
        self.assertTrue(os.path.exists(ANNOTATIONS_FILE))
        annoxml = None
        with io.open(ANNOTATIONS_FILE, 'r', encoding='utf-8') as annof:
            annoxml = xml.etree.ElementTree.parse(annof)
        self.assertTrue(annoxml is not None, 'Failed to parse annotations XML')
        root = annoxml.getroot()
        self.assertEqual(root.tag, 'document')
        annotationsTag = root.find('annotations')
        self.assertEqual(annotationsTag.tag, 'annotations')
        annotations = annotationsTag.findall('annotation')

        # Not all the annotations have TEXT children and the annotations are returned unsorted.
        for a in annotations:
            self.assertEqual(a.tag, 'annotation')
            if a.get('type') == 'text':
                textTag = a.find('TEXT')
                text = textTag.text
                self.assertTrue(text in expected)  # assertIn only added in python 2.7
                # remove the first occurrence, there could be more than one annotation with the same text
                expected.remove(text)
        # We should have seen (and removed) all the expected annotation texts.
        self.assertEqual(len(expected), 0, 'Not all expected annotations were found.')

    def tearDown(self):
        try_rm(ANNOTATIONS_FILE)


if __name__ == '__main__':
    unittest.main()
