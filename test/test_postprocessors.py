#!/usr/bin/env python

from __future__ import unicode_literals

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.postprocessor import MetadataFromFieldPP, MetadataFromTitlePP


class TestMetadataFromField(unittest.TestCase):
    def test_format_to_regex(self):
        pp = MetadataFromFieldPP(None, ['title:%(title)s - %(artist)s'])
        self.assertEqual(pp._data[0]['regex'], r'(?P<title>.+)\ \-\ (?P<artist>.+)')

    def test_field_to_outtmpl(self):
        pp = MetadataFromFieldPP(None, ['title:%(title)s : %(artist)s'])
        self.assertEqual(pp._data[0]['tmpl'], '%(title)s')

    def test_in_out_seperation(self):
        pp = MetadataFromFieldPP(None, ['%(title)s \\: %(artist)s:%(title)s : %(artist)s'])
        self.assertEqual(pp._data[0]['in'], '%(title)s : %(artist)s')
        self.assertEqual(pp._data[0]['out'], '%(title)s : %(artist)s')


class TestMetadataFromTitle(unittest.TestCase):
    def test_format_to_regex(self):
        pp = MetadataFromTitlePP(None, '%(title)s - %(artist)s')
        self.assertEqual(pp._titleregex, r'(?P<title>.+)\ \-\ (?P<artist>.+)')
