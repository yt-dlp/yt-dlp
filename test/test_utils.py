#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest
import warnings
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import contextlib
import io
import itertools
import json
import subprocess
import xml.etree.ElementTree

from yt_dlp.compat import (
    compat_etree_fromstring,
    compat_HTMLParseError,
    compat_os_name,
)
from yt_dlp.utils import (
    Config,
    DateRange,
    ExtractorError,
    InAdvancePagedList,
    LazyList,
    NO_DEFAULT,
    OnDemandPagedList,
    Popen,
    age_restricted,
    args_to_str,
    base_url,
    caesar,
    clean_html,
    clean_podcast_url,
    cli_bool_option,
    cli_option,
    cli_valueless_option,
    date_from_str,
    datetime_from_str,
    detect_exe_version,
    determine_ext,
    determine_file_encoding,
    dfxp2srt,
    encode_base_n,
    encode_compat_str,
    encodeFilename,
    expand_path,
    extract_attributes,
    extract_basic_auth,
    find_xpath_attr,
    fix_xml_ampersands,
    float_or_none,
    format_bytes,
    get_compatible_ext,
    get_element_by_attribute,
    get_element_by_class,
    get_element_html_by_attribute,
    get_element_html_by_class,
    get_element_text_and_html_by_tag,
    get_elements_by_attribute,
    get_elements_by_class,
    get_elements_html_by_attribute,
    get_elements_html_by_class,
    get_elements_text_and_html_by_attribute,
    int_or_none,
    intlist_to_bytes,
    iri_to_uri,
    is_html,
    js_to_json,
    limit_length,
    locked_file,
    lowercase_escape,
    match_str,
    merge_dicts,
    mimetype2ext,
    month_by_name,
    multipart_encode,
    ohdave_rsa_encrypt,
    orderedSet,
    parse_age_limit,
    parse_bitrate,
    parse_codecs,
    parse_count,
    parse_dfxp_time_expr,
    parse_duration,
    parse_filesize,
    parse_iso8601,
    parse_qs,
    parse_resolution,
    pkcs1pad,
    prepend_extension,
    read_batch_urls,
    remove_end,
    remove_quotes,
    remove_start,
    render_table,
    replace_extension,
    rot47,
    sanitize_filename,
    sanitize_path,
    sanitize_url,
    shell_quote,
    smuggle_url,
    str_to_int,
    strip_jsonp,
    strip_or_none,
    subtitles_filename,
    timeconvert,
    try_call,
    unescapeHTML,
    unified_strdate,
    unified_timestamp,
    unsmuggle_url,
    update_url_query,
    uppercase_escape,
    url_basename,
    url_or_none,
    urlencode_postdata,
    urljoin,
    urshift,
    variadic,
    version_tuple,
    xpath_attr,
    xpath_element,
    xpath_text,
    xpath_with_ns,
)
from yt_dlp.utils._utils import _UnsafeExtensionError
from yt_dlp.utils.networking import (
    HTTPHeaderDict,
    escape_rfc3986,
    normalize_url,
    remove_dot_segments,
)


class TestUtil(unittest.TestCase):
    def test_timeconvert(self):
        self.assertTrue(timeconvert('') is None)
        self.assertTrue(timeconvert('bougrg') is None)

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename(''), '')
        self.assertEqual(sanitize_filename('abc'), 'abc')
        self.assertEqual(sanitize_filename('abc_d-e'), 'abc_d-e')

        self.assertEqual(sanitize_filename('123'), '123')

        self.assertEqual('abc⧸de', sanitize_filename('abc/de'))
        self.assertFalse('/' in sanitize_filename('abc/de///'))

        self.assertEqual('abc_de', sanitize_filename('abc/<>\\*|de', is_id=False))
        self.assertEqual('xxx', sanitize_filename('xxx/<>\\*|', is_id=False))
        self.assertEqual('yes no', sanitize_filename('yes? no', is_id=False))
        self.assertEqual('this - that', sanitize_filename('this: that', is_id=False))

        self.assertEqual(sanitize_filename('AT&T'), 'AT&T')
        aumlaut = 'ä'
        self.assertEqual(sanitize_filename(aumlaut), aumlaut)
        tests = '\u043a\u0438\u0440\u0438\u043b\u043b\u0438\u0446\u0430'
        self.assertEqual(sanitize_filename(tests), tests)

        self.assertEqual(
            sanitize_filename('New World record at 0:12:34'),
            'New World record at 0_12_34')

        self.assertEqual(sanitize_filename('--gasdgf'), '--gasdgf')
        self.assertEqual(sanitize_filename('--gasdgf', is_id=True), '--gasdgf')
        self.assertEqual(sanitize_filename('--gasdgf', is_id=False), '_-gasdgf')
        self.assertEqual(sanitize_filename('.gasdgf'), '.gasdgf')
        self.assertEqual(sanitize_filename('.gasdgf', is_id=True), '.gasdgf')
        self.assertEqual(sanitize_filename('.gasdgf', is_id=False), 'gasdgf')

        forbidden = '"\0\\/'
        for fc in forbidden:
            for fbc in forbidden:
                self.assertTrue(fbc not in sanitize_filename(fc))

    def test_sanitize_filename_restricted(self):
        self.assertEqual(sanitize_filename('abc', restricted=True), 'abc')
        self.assertEqual(sanitize_filename('abc_d-e', restricted=True), 'abc_d-e')

        self.assertEqual(sanitize_filename('123', restricted=True), '123')

        self.assertEqual('abc_de', sanitize_filename('abc/de', restricted=True))
        self.assertFalse('/' in sanitize_filename('abc/de///', restricted=True))

        self.assertEqual('abc_de', sanitize_filename('abc/<>\\*|de', restricted=True))
        self.assertEqual('xxx', sanitize_filename('xxx/<>\\*|', restricted=True))
        self.assertEqual('yes_no', sanitize_filename('yes? no', restricted=True))
        self.assertEqual('this_-_that', sanitize_filename('this: that', restricted=True))

        tests = 'aäb\u4e2d\u56fd\u7684c'
        self.assertEqual(sanitize_filename(tests, restricted=True), 'aab_c')
        self.assertTrue(sanitize_filename('\xf6', restricted=True) != '')  # No empty filename

        forbidden = '"\0\\/&!: \'\t\n()[]{}$;`^,#'
        for fc in forbidden:
            for fbc in forbidden:
                self.assertTrue(fbc not in sanitize_filename(fc, restricted=True))

        # Handle a common case more neatly
        self.assertEqual(sanitize_filename('\u5927\u58f0\u5e26 - Song', restricted=True), 'Song')
        self.assertEqual(sanitize_filename('\u603b\u7edf: Speech', restricted=True), 'Speech')
        # .. but make sure the file name is never empty
        self.assertTrue(sanitize_filename('-', restricted=True) != '')
        self.assertTrue(sanitize_filename(':', restricted=True) != '')

        self.assertEqual(sanitize_filename(
            'ÂÃÄÀÁÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖŐØŒÙÚÛÜŰÝÞßàáâãäåæçèéêëìíîïðñòóôõöőøœùúûüűýþÿ', restricted=True),
            'AAAAAAAECEEEEIIIIDNOOOOOOOOEUUUUUYTHssaaaaaaaeceeeeiiiionooooooooeuuuuuythy')

    def test_sanitize_ids(self):
        self.assertEqual(sanitize_filename('_n_cd26wFpw', is_id=True), '_n_cd26wFpw')
        self.assertEqual(sanitize_filename('_BD_eEpuzXw', is_id=True), '_BD_eEpuzXw')
        self.assertEqual(sanitize_filename('N0Y__7-UOdI', is_id=True), 'N0Y__7-UOdI')

    def test_sanitize_path(self):
        if sys.platform != 'win32':
            return

        self.assertEqual(sanitize_path('abc'), 'abc')
        self.assertEqual(sanitize_path('abc/def'), 'abc\\def')
        self.assertEqual(sanitize_path('abc\\def'), 'abc\\def')
        self.assertEqual(sanitize_path('abc|def'), 'abc#def')
        self.assertEqual(sanitize_path('<>:"|?*'), '#######')
        self.assertEqual(sanitize_path('C:/abc/def'), 'C:\\abc\\def')
        self.assertEqual(sanitize_path('C?:/abc/def'), 'C##\\abc\\def')

        self.assertEqual(sanitize_path('\\\\?\\UNC\\ComputerName\\abc'), '\\\\?\\UNC\\ComputerName\\abc')
        self.assertEqual(sanitize_path('\\\\?\\UNC/ComputerName/abc'), '\\\\?\\UNC\\ComputerName\\abc')

        self.assertEqual(sanitize_path('\\\\?\\C:\\abc'), '\\\\?\\C:\\abc')
        self.assertEqual(sanitize_path('\\\\?\\C:/abc'), '\\\\?\\C:\\abc')
        self.assertEqual(sanitize_path('\\\\?\\C:\\ab?c\\de:f'), '\\\\?\\C:\\ab#c\\de#f')
        self.assertEqual(sanitize_path('\\\\?\\C:\\abc'), '\\\\?\\C:\\abc')

        self.assertEqual(
            sanitize_path('youtube/%(uploader)s/%(autonumber)s-%(title)s-%(upload_date)s.%(ext)s'),
            'youtube\\%(uploader)s\\%(autonumber)s-%(title)s-%(upload_date)s.%(ext)s')

        self.assertEqual(
            sanitize_path('youtube/TheWreckingYard ./00001-Not bad, Especially for Free! (1987 Yamaha 700)-20141116.mp4.part'),
            'youtube\\TheWreckingYard #\\00001-Not bad, Especially for Free! (1987 Yamaha 700)-20141116.mp4.part')
        self.assertEqual(sanitize_path('abc/def...'), 'abc\\def..#')
        self.assertEqual(sanitize_path('abc.../def'), 'abc..#\\def')
        self.assertEqual(sanitize_path('abc.../def...'), 'abc..#\\def..#')

        self.assertEqual(sanitize_path('../abc'), '..\\abc')
        self.assertEqual(sanitize_path('../../abc'), '..\\..\\abc')
        self.assertEqual(sanitize_path('./abc'), 'abc')
        self.assertEqual(sanitize_path('./../abc'), '..\\abc')

    def test_sanitize_url(self):
        self.assertEqual(sanitize_url('//foo.bar'), 'http://foo.bar')
        self.assertEqual(sanitize_url('httpss://foo.bar'), 'https://foo.bar')
        self.assertEqual(sanitize_url('rmtps://foo.bar'), 'rtmps://foo.bar')
        self.assertEqual(sanitize_url('https://foo.bar'), 'https://foo.bar')
        self.assertEqual(sanitize_url('foo bar'), 'foo bar')

    def test_expand_path(self):
        def env(var):
            return f'%{var}%' if sys.platform == 'win32' else f'${var}'

        os.environ['yt_dlp_EXPATH_PATH'] = 'expanded'
        self.assertEqual(expand_path(env('yt_dlp_EXPATH_PATH')), 'expanded')

        old_home = os.environ.get('HOME')
        test_str = R'C:\Documents and Settings\тест\Application Data'
        try:
            os.environ['HOME'] = test_str
            self.assertEqual(expand_path(env('HOME')), os.getenv('HOME'))
            self.assertEqual(expand_path('~'), os.getenv('HOME'))
            self.assertEqual(
                expand_path('~/{}'.format(env('yt_dlp_EXPATH_PATH'))),
                '{}/expanded'.format(os.getenv('HOME')))
        finally:
            os.environ['HOME'] = old_home or ''

    _uncommon_extensions = [
        ('exe', 'abc.exe.ext'),
        ('de', 'abc.de.ext'),
        ('../.mp4', None),
        ('..\\.mp4', None),
    ]

    def test_prepend_extension(self):
        self.assertEqual(prepend_extension('abc.ext', 'temp'), 'abc.temp.ext')
        self.assertEqual(prepend_extension('abc.ext', 'temp', 'ext'), 'abc.temp.ext')
        self.assertEqual(prepend_extension('abc.unexpected_ext', 'temp', 'ext'), 'abc.unexpected_ext.temp')
        self.assertEqual(prepend_extension('abc', 'temp'), 'abc.temp')
        self.assertEqual(prepend_extension('.abc', 'temp'), '.abc.temp')
        self.assertEqual(prepend_extension('.abc.ext', 'temp'), '.abc.temp.ext')

        # Test uncommon extensions
        self.assertEqual(prepend_extension('abc.ext', 'bin'), 'abc.bin.ext')
        for ext, result in self._uncommon_extensions:
            with self.assertRaises(_UnsafeExtensionError):
                prepend_extension('abc', ext)
            if result:
                self.assertEqual(prepend_extension('abc.ext', ext, 'ext'), result)
            else:
                with self.assertRaises(_UnsafeExtensionError):
                    prepend_extension('abc.ext', ext, 'ext')
            with self.assertRaises(_UnsafeExtensionError):
                prepend_extension('abc.unexpected_ext', ext, 'ext')

    def test_replace_extension(self):
        self.assertEqual(replace_extension('abc.ext', 'temp'), 'abc.temp')
        self.assertEqual(replace_extension('abc.ext', 'temp', 'ext'), 'abc.temp')
        self.assertEqual(replace_extension('abc.unexpected_ext', 'temp', 'ext'), 'abc.unexpected_ext.temp')
        self.assertEqual(replace_extension('abc', 'temp'), 'abc.temp')
        self.assertEqual(replace_extension('.abc', 'temp'), '.abc.temp')
        self.assertEqual(replace_extension('.abc.ext', 'temp'), '.abc.temp')

        # Test uncommon extensions
        self.assertEqual(replace_extension('abc.ext', 'bin'), 'abc.unknown_video')
        for ext, _ in self._uncommon_extensions:
            with self.assertRaises(_UnsafeExtensionError):
                replace_extension('abc', ext)
            with self.assertRaises(_UnsafeExtensionError):
                replace_extension('abc.ext', ext, 'ext')
            with self.assertRaises(_UnsafeExtensionError):
                replace_extension('abc.unexpected_ext', ext, 'ext')

    def test_subtitles_filename(self):
        self.assertEqual(subtitles_filename('abc.ext', 'en', 'vtt'), 'abc.en.vtt')
        self.assertEqual(subtitles_filename('abc.ext', 'en', 'vtt', 'ext'), 'abc.en.vtt')
        self.assertEqual(subtitles_filename('abc.unexpected_ext', 'en', 'vtt', 'ext'), 'abc.unexpected_ext.en.vtt')

    def test_remove_start(self):
        self.assertEqual(remove_start(None, 'A - '), None)
        self.assertEqual(remove_start('A - B', 'A - '), 'B')
        self.assertEqual(remove_start('B - A', 'A - '), 'B - A')

    def test_remove_end(self):
        self.assertEqual(remove_end(None, ' - B'), None)
        self.assertEqual(remove_end('A - B', ' - B'), 'A')
        self.assertEqual(remove_end('B - A', ' - B'), 'B - A')

    def test_remove_quotes(self):
        self.assertEqual(remove_quotes(None), None)
        self.assertEqual(remove_quotes('"'), '"')
        self.assertEqual(remove_quotes("'"), "'")
        self.assertEqual(remove_quotes(';'), ';')
        self.assertEqual(remove_quotes('";'), '";')
        self.assertEqual(remove_quotes('""'), '')
        self.assertEqual(remove_quotes('";"'), ';')

    def test_ordered_set(self):
        self.assertEqual(orderedSet([1, 1, 2, 3, 4, 4, 5, 6, 7, 3, 5]), [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(orderedSet([]), [])
        self.assertEqual(orderedSet([1]), [1])
        # keep the list ordered
        self.assertEqual(orderedSet([135, 1, 1, 1]), [135, 1])

    def test_unescape_html(self):
        self.assertEqual(unescapeHTML('%20;'), '%20;')
        self.assertEqual(unescapeHTML('&#x2F;'), '/')
        self.assertEqual(unescapeHTML('&#47;'), '/')
        self.assertEqual(unescapeHTML('&eacute;'), 'é')
        self.assertEqual(unescapeHTML('&#2013266066;'), '&#2013266066;')
        self.assertEqual(unescapeHTML('&a&quot;'), '&a"')
        # HTML5 entities
        self.assertEqual(unescapeHTML('&period;&apos;'), '.\'')

    def test_date_from_str(self):
        self.assertEqual(date_from_str('yesterday'), date_from_str('now-1day'))
        self.assertEqual(date_from_str('now+7day'), date_from_str('now+1week'))
        self.assertEqual(date_from_str('now+14day'), date_from_str('now+2week'))
        self.assertEqual(date_from_str('20200229+365day'), date_from_str('20200229+1year'))
        self.assertEqual(date_from_str('20210131+28day'), date_from_str('20210131+1month'))

    def test_datetime_from_str(self):
        self.assertEqual(datetime_from_str('yesterday', precision='day'), datetime_from_str('now-1day', precision='auto'))
        self.assertEqual(datetime_from_str('now+7day', precision='day'), datetime_from_str('now+1week', precision='auto'))
        self.assertEqual(datetime_from_str('now+14day', precision='day'), datetime_from_str('now+2week', precision='auto'))
        self.assertEqual(datetime_from_str('20200229+365day', precision='day'), datetime_from_str('20200229+1year', precision='auto'))
        self.assertEqual(datetime_from_str('20210131+28day', precision='day'), datetime_from_str('20210131+1month', precision='auto'))
        self.assertEqual(datetime_from_str('20210131+59day', precision='day'), datetime_from_str('20210131+2month', precision='auto'))
        self.assertEqual(datetime_from_str('now+1day', precision='hour'), datetime_from_str('now+24hours', precision='auto'))
        self.assertEqual(datetime_from_str('now+23hours', precision='hour'), datetime_from_str('now+23hours', precision='auto'))

    def test_daterange(self):
        _20century = DateRange('19000101', '20000101')
        self.assertFalse('17890714' in _20century)
        _ac = DateRange('00010101')
        self.assertTrue('19690721' in _ac)
        _firstmilenium = DateRange(end='10000101')
        self.assertTrue('07110427' in _firstmilenium)

    def test_unified_dates(self):
        self.assertEqual(unified_strdate('December 21, 2010'), '20101221')
        self.assertEqual(unified_strdate('8/7/2009'), '20090708')
        self.assertEqual(unified_strdate('Dec 14, 2012'), '20121214')
        self.assertEqual(unified_strdate('2012/10/11 01:56:38 +0000'), '20121011')
        self.assertEqual(unified_strdate('1968 12 10'), '19681210')
        self.assertEqual(unified_strdate('1968-12-10'), '19681210')
        self.assertEqual(unified_strdate('31-07-2022 20:00'), '20220731')
        self.assertEqual(unified_strdate('28/01/2014 21:00:00 +0100'), '20140128')
        self.assertEqual(
            unified_strdate('11/26/2014 11:30:00 AM PST', day_first=False),
            '20141126')
        self.assertEqual(
            unified_strdate('2/2/2015 6:47:40 PM', day_first=False),
            '20150202')
        self.assertEqual(unified_strdate('Feb 14th 2016 5:45PM'), '20160214')
        self.assertEqual(unified_strdate('25-09-2014'), '20140925')
        self.assertEqual(unified_strdate('27.02.2016 17:30'), '20160227')
        self.assertEqual(unified_strdate('UNKNOWN DATE FORMAT'), None)
        self.assertEqual(unified_strdate('Feb 7, 2016 at 6:35 pm'), '20160207')
        self.assertEqual(unified_strdate('July 15th, 2013'), '20130715')
        self.assertEqual(unified_strdate('September 1st, 2013'), '20130901')
        self.assertEqual(unified_strdate('Sep 2nd, 2013'), '20130902')
        self.assertEqual(unified_strdate('November 3rd, 2019'), '20191103')
        self.assertEqual(unified_strdate('October 23rd, 2005'), '20051023')

    def test_unified_timestamps(self):
        self.assertEqual(unified_timestamp('December 21, 2010'), 1292889600)
        self.assertEqual(unified_timestamp('8/7/2009'), 1247011200)
        self.assertEqual(unified_timestamp('Dec 14, 2012'), 1355443200)
        self.assertEqual(unified_timestamp('2012/10/11 01:56:38 +0000'), 1349920598)
        self.assertEqual(unified_timestamp('1968 12 10'), -33436800)
        self.assertEqual(unified_timestamp('1968-12-10'), -33436800)
        self.assertEqual(unified_timestamp('28/01/2014 21:00:00 +0100'), 1390939200)
        self.assertEqual(
            unified_timestamp('11/26/2014 11:30:00 AM PST', day_first=False),
            1417001400)
        self.assertEqual(
            unified_timestamp('2/2/2015 6:47:40 PM', day_first=False),
            1422902860)
        self.assertEqual(unified_timestamp('Feb 14th 2016 5:45PM'), 1455471900)
        self.assertEqual(unified_timestamp('25-09-2014'), 1411603200)
        self.assertEqual(unified_timestamp('27.02.2016 17:30'), 1456594200)
        self.assertEqual(unified_timestamp('UNKNOWN DATE FORMAT'), None)
        self.assertEqual(unified_timestamp('May 16, 2016 11:15 PM'), 1463440500)
        self.assertEqual(unified_timestamp('Feb 7, 2016 at 6:35 pm'), 1454870100)
        self.assertEqual(unified_timestamp('2017-03-30T17:52:41Q'), 1490896361)
        self.assertEqual(unified_timestamp('Sep 11, 2013 | 5:49 AM'), 1378878540)
        self.assertEqual(unified_timestamp('December 15, 2017 at 7:49 am'), 1513324140)
        self.assertEqual(unified_timestamp('2018-03-14T08:32:43.1493874+00:00'), 1521016363)
        self.assertEqual(unified_timestamp('Sunday, 26 Nov 2006, 19:00'), 1164567600)
        self.assertEqual(unified_timestamp('wed, aug 16, 2008, 12:00pm'), 1218931200)

        self.assertEqual(unified_timestamp('December 31 1969 20:00:01 EDT'), 1)
        self.assertEqual(unified_timestamp('Wednesday 31 December 1969 18:01:26 MDT'), 86)
        self.assertEqual(unified_timestamp('12/31/1969 20:01:18 EDT', False), 78)

    def test_determine_ext(self):
        self.assertEqual(determine_ext('http://example.com/foo/bar.mp4/?download'), 'mp4')
        self.assertEqual(determine_ext('http://example.com/foo/bar/?download', None), None)
        self.assertEqual(determine_ext('http://example.com/foo/bar.nonext/?download', None), None)
        self.assertEqual(determine_ext('http://example.com/foo/bar/mp4?download', None), None)
        self.assertEqual(determine_ext('http://example.com/foo/bar.m3u8//?download'), 'm3u8')
        self.assertEqual(determine_ext('foobar', None), None)

    def test_find_xpath_attr(self):
        testxml = '''<root>
            <node/>
            <node x="a"/>
            <node x="a" y="c" />
            <node x="b" y="d" />
            <node x="" />
        </root>'''
        doc = compat_etree_fromstring(testxml)

        self.assertEqual(find_xpath_attr(doc, './/fourohfour', 'n'), None)
        self.assertEqual(find_xpath_attr(doc, './/fourohfour', 'n', 'v'), None)
        self.assertEqual(find_xpath_attr(doc, './/node', 'n'), None)
        self.assertEqual(find_xpath_attr(doc, './/node', 'n', 'v'), None)
        self.assertEqual(find_xpath_attr(doc, './/node', 'x'), doc[1])
        self.assertEqual(find_xpath_attr(doc, './/node', 'x', 'a'), doc[1])
        self.assertEqual(find_xpath_attr(doc, './/node', 'x', 'b'), doc[3])
        self.assertEqual(find_xpath_attr(doc, './/node', 'y'), doc[2])
        self.assertEqual(find_xpath_attr(doc, './/node', 'y', 'c'), doc[2])
        self.assertEqual(find_xpath_attr(doc, './/node', 'y', 'd'), doc[3])
        self.assertEqual(find_xpath_attr(doc, './/node', 'x', ''), doc[4])

    def test_xpath_with_ns(self):
        testxml = '''<root xmlns:media="http://example.com/">
            <media:song>
                <media:author>The Author</media:author>
                <url>http://server.com/download.mp3</url>
            </media:song>
        </root>'''
        doc = compat_etree_fromstring(testxml)
        find = lambda p: doc.find(xpath_with_ns(p, {'media': 'http://example.com/'}))
        self.assertTrue(find('media:song') is not None)
        self.assertEqual(find('media:song/media:author').text, 'The Author')
        self.assertEqual(find('media:song/url').text, 'http://server.com/download.mp3')

    def test_xpath_element(self):
        doc = xml.etree.ElementTree.Element('root')
        div = xml.etree.ElementTree.SubElement(doc, 'div')
        p = xml.etree.ElementTree.SubElement(div, 'p')
        p.text = 'Foo'
        self.assertEqual(xpath_element(doc, 'div/p'), p)
        self.assertEqual(xpath_element(doc, ['div/p']), p)
        self.assertEqual(xpath_element(doc, ['div/bar', 'div/p']), p)
        self.assertEqual(xpath_element(doc, 'div/bar', default='default'), 'default')
        self.assertEqual(xpath_element(doc, ['div/bar'], default='default'), 'default')
        self.assertTrue(xpath_element(doc, 'div/bar') is None)
        self.assertTrue(xpath_element(doc, ['div/bar']) is None)
        self.assertTrue(xpath_element(doc, ['div/bar'], 'div/baz') is None)
        self.assertRaises(ExtractorError, xpath_element, doc, 'div/bar', fatal=True)
        self.assertRaises(ExtractorError, xpath_element, doc, ['div/bar'], fatal=True)
        self.assertRaises(ExtractorError, xpath_element, doc, ['div/bar', 'div/baz'], fatal=True)

    def test_xpath_text(self):
        testxml = '''<root>
            <div>
                <p>Foo</p>
            </div>
        </root>'''
        doc = compat_etree_fromstring(testxml)
        self.assertEqual(xpath_text(doc, 'div/p'), 'Foo')
        self.assertEqual(xpath_text(doc, 'div/bar', default='default'), 'default')
        self.assertTrue(xpath_text(doc, 'div/bar') is None)
        self.assertRaises(ExtractorError, xpath_text, doc, 'div/bar', fatal=True)

    def test_xpath_attr(self):
        testxml = '''<root>
            <div>
                <p x="a">Foo</p>
            </div>
        </root>'''
        doc = compat_etree_fromstring(testxml)
        self.assertEqual(xpath_attr(doc, 'div/p', 'x'), 'a')
        self.assertEqual(xpath_attr(doc, 'div/bar', 'x'), None)
        self.assertEqual(xpath_attr(doc, 'div/p', 'y'), None)
        self.assertEqual(xpath_attr(doc, 'div/bar', 'x', default='default'), 'default')
        self.assertEqual(xpath_attr(doc, 'div/p', 'y', default='default'), 'default')
        self.assertRaises(ExtractorError, xpath_attr, doc, 'div/bar', 'x', fatal=True)
        self.assertRaises(ExtractorError, xpath_attr, doc, 'div/p', 'y', fatal=True)

    def test_smuggle_url(self):
        data = {'ö': 'ö', 'abc': [3]}
        url = 'https://foo.bar/baz?x=y#a'
        smug_url = smuggle_url(url, data)
        unsmug_url, unsmug_data = unsmuggle_url(smug_url)
        self.assertEqual(url, unsmug_url)
        self.assertEqual(data, unsmug_data)

        res_url, res_data = unsmuggle_url(url)
        self.assertEqual(res_url, url)
        self.assertEqual(res_data, None)

        smug_url = smuggle_url(url, {'a': 'b'})
        smug_smug_url = smuggle_url(smug_url, {'c': 'd'})
        res_url, res_data = unsmuggle_url(smug_smug_url)
        self.assertEqual(res_url, url)
        self.assertEqual(res_data, {'a': 'b', 'c': 'd'})

    def test_shell_quote(self):
        args = ['ffmpeg', '-i', encodeFilename('ñ€ß\'.mp4')]
        self.assertEqual(
            shell_quote(args),
            """ffmpeg -i 'ñ€ß'"'"'.mp4'""" if compat_os_name != 'nt' else '''ffmpeg -i "ñ€ß'.mp4"''')

    def test_float_or_none(self):
        self.assertEqual(float_or_none('42.42'), 42.42)
        self.assertEqual(float_or_none('42'), 42.0)
        self.assertEqual(float_or_none(''), None)
        self.assertEqual(float_or_none(None), None)
        self.assertEqual(float_or_none([]), None)
        self.assertEqual(float_or_none(set()), None)

    def test_int_or_none(self):
        self.assertEqual(int_or_none('42'), 42)
        self.assertEqual(int_or_none(''), None)
        self.assertEqual(int_or_none(None), None)
        self.assertEqual(int_or_none([]), None)
        self.assertEqual(int_or_none(set()), None)

    def test_str_to_int(self):
        self.assertEqual(str_to_int('123,456'), 123456)
        self.assertEqual(str_to_int('123.456'), 123456)
        self.assertEqual(str_to_int(523), 523)
        self.assertEqual(str_to_int('noninteger'), None)
        self.assertEqual(str_to_int([]), None)

    def test_url_basename(self):
        self.assertEqual(url_basename('http://foo.de/'), '')
        self.assertEqual(url_basename('http://foo.de/bar/baz'), 'baz')
        self.assertEqual(url_basename('http://foo.de/bar/baz?x=y'), 'baz')
        self.assertEqual(url_basename('http://foo.de/bar/baz#x=y'), 'baz')
        self.assertEqual(url_basename('http://foo.de/bar/baz/'), 'baz')
        self.assertEqual(
            url_basename('http://media.w3.org/2010/05/sintel/trailer.mp4'),
            'trailer.mp4')

    def test_base_url(self):
        self.assertEqual(base_url('http://foo.de/'), 'http://foo.de/')
        self.assertEqual(base_url('http://foo.de/bar'), 'http://foo.de/')
        self.assertEqual(base_url('http://foo.de/bar/'), 'http://foo.de/bar/')
        self.assertEqual(base_url('http://foo.de/bar/baz'), 'http://foo.de/bar/')
        self.assertEqual(base_url('http://foo.de/bar/baz?x=z/x/c'), 'http://foo.de/bar/')
        self.assertEqual(base_url('http://foo.de/bar/baz&x=z&w=y/x/c'), 'http://foo.de/bar/baz&x=z&w=y/x/')

    def test_urljoin(self):
        self.assertEqual(urljoin('http://foo.de/', '/a/b/c.txt'), 'http://foo.de/a/b/c.txt')
        self.assertEqual(urljoin(b'http://foo.de/', '/a/b/c.txt'), 'http://foo.de/a/b/c.txt')
        self.assertEqual(urljoin('http://foo.de/', b'/a/b/c.txt'), 'http://foo.de/a/b/c.txt')
        self.assertEqual(urljoin(b'http://foo.de/', b'/a/b/c.txt'), 'http://foo.de/a/b/c.txt')
        self.assertEqual(urljoin('//foo.de/', '/a/b/c.txt'), '//foo.de/a/b/c.txt')
        self.assertEqual(urljoin('http://foo.de/', 'a/b/c.txt'), 'http://foo.de/a/b/c.txt')
        self.assertEqual(urljoin('http://foo.de', '/a/b/c.txt'), 'http://foo.de/a/b/c.txt')
        self.assertEqual(urljoin('http://foo.de', 'a/b/c.txt'), 'http://foo.de/a/b/c.txt')
        self.assertEqual(urljoin('http://foo.de/', 'http://foo.de/a/b/c.txt'), 'http://foo.de/a/b/c.txt')
        self.assertEqual(urljoin('http://foo.de/', '//foo.de/a/b/c.txt'), '//foo.de/a/b/c.txt')
        self.assertEqual(urljoin(None, 'http://foo.de/a/b/c.txt'), 'http://foo.de/a/b/c.txt')
        self.assertEqual(urljoin(None, '//foo.de/a/b/c.txt'), '//foo.de/a/b/c.txt')
        self.assertEqual(urljoin('', 'http://foo.de/a/b/c.txt'), 'http://foo.de/a/b/c.txt')
        self.assertEqual(urljoin(['foobar'], 'http://foo.de/a/b/c.txt'), 'http://foo.de/a/b/c.txt')
        self.assertEqual(urljoin('http://foo.de/', None), None)
        self.assertEqual(urljoin('http://foo.de/', ''), None)
        self.assertEqual(urljoin('http://foo.de/', ['foobar']), None)
        self.assertEqual(urljoin('http://foo.de/a/b/c.txt', '.././../d.txt'), 'http://foo.de/d.txt')
        self.assertEqual(urljoin('http://foo.de/a/b/c.txt', 'rtmp://foo.de'), 'rtmp://foo.de')
        self.assertEqual(urljoin(None, 'rtmp://foo.de'), 'rtmp://foo.de')

    def test_url_or_none(self):
        self.assertEqual(url_or_none(None), None)
        self.assertEqual(url_or_none(''), None)
        self.assertEqual(url_or_none('foo'), None)
        self.assertEqual(url_or_none('http://foo.de'), 'http://foo.de')
        self.assertEqual(url_or_none('https://foo.de'), 'https://foo.de')
        self.assertEqual(url_or_none('http$://foo.de'), None)
        self.assertEqual(url_or_none('http://foo.de'), 'http://foo.de')
        self.assertEqual(url_or_none('//foo.de'), '//foo.de')
        self.assertEqual(url_or_none('s3://foo.de'), None)
        self.assertEqual(url_or_none('rtmpte://foo.de'), 'rtmpte://foo.de')
        self.assertEqual(url_or_none('mms://foo.de'), 'mms://foo.de')
        self.assertEqual(url_or_none('rtspu://foo.de'), 'rtspu://foo.de')
        self.assertEqual(url_or_none('ftps://foo.de'), 'ftps://foo.de')

    def test_parse_age_limit(self):
        self.assertEqual(parse_age_limit(None), None)
        self.assertEqual(parse_age_limit(False), None)
        self.assertEqual(parse_age_limit('invalid'), None)
        self.assertEqual(parse_age_limit(0), 0)
        self.assertEqual(parse_age_limit(18), 18)
        self.assertEqual(parse_age_limit(21), 21)
        self.assertEqual(parse_age_limit(22), None)
        self.assertEqual(parse_age_limit('18'), 18)
        self.assertEqual(parse_age_limit('18+'), 18)
        self.assertEqual(parse_age_limit('PG-13'), 13)
        self.assertEqual(parse_age_limit('TV-14'), 14)
        self.assertEqual(parse_age_limit('TV-MA'), 17)
        self.assertEqual(parse_age_limit('TV14'), 14)
        self.assertEqual(parse_age_limit('TV_G'), 0)

    def test_parse_duration(self):
        self.assertEqual(parse_duration(None), None)
        self.assertEqual(parse_duration(False), None)
        self.assertEqual(parse_duration('invalid'), None)
        self.assertEqual(parse_duration('1'), 1)
        self.assertEqual(parse_duration('1337:12'), 80232)
        self.assertEqual(parse_duration('9:12:43'), 33163)
        self.assertEqual(parse_duration('12:00'), 720)
        self.assertEqual(parse_duration('00:01:01'), 61)
        self.assertEqual(parse_duration('x:y'), None)
        self.assertEqual(parse_duration('3h11m53s'), 11513)
        self.assertEqual(parse_duration('3h 11m 53s'), 11513)
        self.assertEqual(parse_duration('3 hours 11 minutes 53 seconds'), 11513)
        self.assertEqual(parse_duration('3 hours 11 mins 53 secs'), 11513)
        self.assertEqual(parse_duration('3 hours, 11 minutes, 53 seconds'), 11513)
        self.assertEqual(parse_duration('3 hours, 11 mins, 53 secs'), 11513)
        self.assertEqual(parse_duration('62m45s'), 3765)
        self.assertEqual(parse_duration('6m59s'), 419)
        self.assertEqual(parse_duration('49s'), 49)
        self.assertEqual(parse_duration('0h0m0s'), 0)
        self.assertEqual(parse_duration('0m0s'), 0)
        self.assertEqual(parse_duration('0s'), 0)
        self.assertEqual(parse_duration('01:02:03.05'), 3723.05)
        self.assertEqual(parse_duration('T30M38S'), 1838)
        self.assertEqual(parse_duration('5 s'), 5)
        self.assertEqual(parse_duration('3 min'), 180)
        self.assertEqual(parse_duration('2.5 hours'), 9000)
        self.assertEqual(parse_duration('02:03:04'), 7384)
        self.assertEqual(parse_duration('01:02:03:04'), 93784)
        self.assertEqual(parse_duration('1 hour 3 minutes'), 3780)
        self.assertEqual(parse_duration('87 Min.'), 5220)
        self.assertEqual(parse_duration('PT1H0.040S'), 3600.04)
        self.assertEqual(parse_duration('PT00H03M30SZ'), 210)
        self.assertEqual(parse_duration('P0Y0M0DT0H4M20.880S'), 260.88)
        self.assertEqual(parse_duration('01:02:03:050'), 3723.05)
        self.assertEqual(parse_duration('103:050'), 103.05)
        self.assertEqual(parse_duration('1HR 3MIN'), 3780)
        self.assertEqual(parse_duration('2hrs 3mins'), 7380)

    def test_fix_xml_ampersands(self):
        self.assertEqual(
            fix_xml_ampersands('"&x=y&z=a'), '"&amp;x=y&amp;z=a')
        self.assertEqual(
            fix_xml_ampersands('"&amp;x=y&wrong;&z=a'),
            '"&amp;x=y&amp;wrong;&amp;z=a')
        self.assertEqual(
            fix_xml_ampersands('&amp;&apos;&gt;&lt;&quot;'),
            '&amp;&apos;&gt;&lt;&quot;')
        self.assertEqual(
            fix_xml_ampersands('&#1234;&#x1abC;'), '&#1234;&#x1abC;')
        self.assertEqual(fix_xml_ampersands('&#&#'), '&amp;#&amp;#')

    def test_paged_list(self):
        def testPL(size, pagesize, sliceargs, expected):
            def get_page(pagenum):
                firstid = pagenum * pagesize
                upto = min(size, pagenum * pagesize + pagesize)
                yield from range(firstid, upto)

            pl = OnDemandPagedList(get_page, pagesize)
            got = pl.getslice(*sliceargs)
            self.assertEqual(got, expected)

            iapl = InAdvancePagedList(get_page, size // pagesize + 1, pagesize)
            got = iapl.getslice(*sliceargs)
            self.assertEqual(got, expected)

        testPL(5, 2, (), [0, 1, 2, 3, 4])
        testPL(5, 2, (1,), [1, 2, 3, 4])
        testPL(5, 2, (2,), [2, 3, 4])
        testPL(5, 2, (4,), [4])
        testPL(5, 2, (0, 3), [0, 1, 2])
        testPL(5, 2, (1, 4), [1, 2, 3])
        testPL(5, 2, (2, 99), [2, 3, 4])
        testPL(5, 2, (20, 99), [])

    def test_read_batch_urls(self):
        f = io.StringIO('''\xef\xbb\xbf foo
            bar\r
            baz
            # More after this line\r
            ; or after this
            bam''')
        self.assertEqual(read_batch_urls(f), ['foo', 'bar', 'baz', 'bam'])

    def test_urlencode_postdata(self):
        data = urlencode_postdata({'username': 'foo@bar.com', 'password': '1234'})
        self.assertTrue(isinstance(data, bytes))

    def test_update_url_query(self):
        self.assertEqual(parse_qs(update_url_query(
            'http://example.com/path', {'quality': ['HD'], 'format': ['mp4']})),
            parse_qs('http://example.com/path?quality=HD&format=mp4'))
        self.assertEqual(parse_qs(update_url_query(
            'http://example.com/path', {'system': ['LINUX', 'WINDOWS']})),
            parse_qs('http://example.com/path?system=LINUX&system=WINDOWS'))
        self.assertEqual(parse_qs(update_url_query(
            'http://example.com/path', {'fields': 'id,formats,subtitles'})),
            parse_qs('http://example.com/path?fields=id,formats,subtitles'))
        self.assertEqual(parse_qs(update_url_query(
            'http://example.com/path', {'fields': ('id,formats,subtitles', 'thumbnails')})),
            parse_qs('http://example.com/path?fields=id,formats,subtitles&fields=thumbnails'))
        self.assertEqual(parse_qs(update_url_query(
            'http://example.com/path?manifest=f4m', {'manifest': []})),
            parse_qs('http://example.com/path'))
        self.assertEqual(parse_qs(update_url_query(
            'http://example.com/path?system=LINUX&system=WINDOWS', {'system': 'LINUX'})),
            parse_qs('http://example.com/path?system=LINUX'))
        self.assertEqual(parse_qs(update_url_query(
            'http://example.com/path', {'fields': b'id,formats,subtitles'})),
            parse_qs('http://example.com/path?fields=id,formats,subtitles'))
        self.assertEqual(parse_qs(update_url_query(
            'http://example.com/path', {'width': 1080, 'height': 720})),
            parse_qs('http://example.com/path?width=1080&height=720'))
        self.assertEqual(parse_qs(update_url_query(
            'http://example.com/path', {'bitrate': 5020.43})),
            parse_qs('http://example.com/path?bitrate=5020.43'))
        self.assertEqual(parse_qs(update_url_query(
            'http://example.com/path', {'test': '第二行тест'})),
            parse_qs('http://example.com/path?test=%E7%AC%AC%E4%BA%8C%E8%A1%8C%D1%82%D0%B5%D1%81%D1%82'))

    def test_multipart_encode(self):
        self.assertEqual(
            multipart_encode({b'field': b'value'}, boundary='AAAAAA')[0],
            b'--AAAAAA\r\nContent-Disposition: form-data; name="field"\r\n\r\nvalue\r\n--AAAAAA--\r\n')
        self.assertEqual(
            multipart_encode({'欄位'.encode(): '值'.encode()}, boundary='AAAAAA')[0],
            b'--AAAAAA\r\nContent-Disposition: form-data; name="\xe6\xac\x84\xe4\xbd\x8d"\r\n\r\n\xe5\x80\xbc\r\n--AAAAAA--\r\n')
        self.assertRaises(
            ValueError, multipart_encode, {b'field': b'value'}, boundary='value')

    def test_merge_dicts(self):
        self.assertEqual(merge_dicts({'a': 1}, {'b': 2}), {'a': 1, 'b': 2})
        self.assertEqual(merge_dicts({'a': 1}, {'a': 2}), {'a': 1})
        self.assertEqual(merge_dicts({'a': 1}, {'a': None}), {'a': 1})
        self.assertEqual(merge_dicts({'a': 1}, {'a': ''}), {'a': 1})
        self.assertEqual(merge_dicts({'a': 1}, {}), {'a': 1})
        self.assertEqual(merge_dicts({'a': None}, {'a': 1}), {'a': 1})
        self.assertEqual(merge_dicts({'a': ''}, {'a': 1}), {'a': ''})
        self.assertEqual(merge_dicts({'a': ''}, {'a': 'abc'}), {'a': 'abc'})
        self.assertEqual(merge_dicts({'a': None}, {'a': ''}, {'a': 'abc'}), {'a': 'abc'})

    def test_encode_compat_str(self):
        self.assertEqual(encode_compat_str(b'\xd1\x82\xd0\xb5\xd1\x81\xd1\x82', 'utf-8'), 'тест')
        self.assertEqual(encode_compat_str('тест', 'utf-8'), 'тест')

    def test_parse_iso8601(self):
        self.assertEqual(parse_iso8601('2014-03-23T23:04:26+0100'), 1395612266)
        self.assertEqual(parse_iso8601('2014-03-23T23:04:26-07:00'), 1395641066)
        self.assertEqual(parse_iso8601('2014-03-23T23:04:26', timezone=dt.timedelta(hours=-7)), 1395641066)
        self.assertEqual(parse_iso8601('2014-03-23T23:04:26', timezone=NO_DEFAULT), None)
        # default does not override timezone in date_str
        self.assertEqual(parse_iso8601('2014-03-23T23:04:26-07:00', timezone=dt.timedelta(hours=-10)), 1395641066)
        self.assertEqual(parse_iso8601('2014-03-23T22:04:26+0000'), 1395612266)
        self.assertEqual(parse_iso8601('2014-03-23T22:04:26Z'), 1395612266)
        self.assertEqual(parse_iso8601('2014-03-23T22:04:26.1234Z'), 1395612266)
        self.assertEqual(parse_iso8601('2015-09-29T08:27:31.727'), 1443515251)
        self.assertEqual(parse_iso8601('2015-09-29T08-27-31.727'), None)

    def test_strip_jsonp(self):
        stripped = strip_jsonp('cb ([ {"id":"532cb",\n\n\n"x":\n3}\n]\n);')
        d = json.loads(stripped)
        self.assertEqual(d, [{'id': '532cb', 'x': 3}])

        stripped = strip_jsonp('parseMetadata({"STATUS":"OK"})\n\n\n//epc')
        d = json.loads(stripped)
        self.assertEqual(d, {'STATUS': 'OK'})

        stripped = strip_jsonp('ps.embedHandler({"status": "success"});')
        d = json.loads(stripped)
        self.assertEqual(d, {'status': 'success'})

        stripped = strip_jsonp('window.cb && window.cb({"status": "success"});')
        d = json.loads(stripped)
        self.assertEqual(d, {'status': 'success'})

        stripped = strip_jsonp('window.cb && cb({"status": "success"});')
        d = json.loads(stripped)
        self.assertEqual(d, {'status': 'success'})

        stripped = strip_jsonp('({"status": "success"});')
        d = json.loads(stripped)
        self.assertEqual(d, {'status': 'success'})

    def test_strip_or_none(self):
        self.assertEqual(strip_or_none(' abc'), 'abc')
        self.assertEqual(strip_or_none('abc '), 'abc')
        self.assertEqual(strip_or_none(' abc '), 'abc')
        self.assertEqual(strip_or_none('\tabc\t'), 'abc')
        self.assertEqual(strip_or_none('\n\tabc\n\t'), 'abc')
        self.assertEqual(strip_or_none('abc'), 'abc')
        self.assertEqual(strip_or_none(''), '')
        self.assertEqual(strip_or_none(None), None)
        self.assertEqual(strip_or_none(42), None)
        self.assertEqual(strip_or_none([]), None)

    def test_uppercase_escape(self):
        self.assertEqual(uppercase_escape('aä'), 'aä')
        self.assertEqual(uppercase_escape('\\U0001d550'), '𝕐')

    def test_lowercase_escape(self):
        self.assertEqual(lowercase_escape('aä'), 'aä')
        self.assertEqual(lowercase_escape('\\u0026'), '&')

    def test_limit_length(self):
        self.assertEqual(limit_length(None, 12), None)
        self.assertEqual(limit_length('foo', 12), 'foo')
        self.assertTrue(
            limit_length('foo bar baz asd', 12).startswith('foo bar'))
        self.assertTrue('...' in limit_length('foo bar baz asd', 12))

    def test_mimetype2ext(self):
        self.assertEqual(mimetype2ext(None), None)
        self.assertEqual(mimetype2ext('video/x-flv'), 'flv')
        self.assertEqual(mimetype2ext('application/x-mpegURL'), 'm3u8')
        self.assertEqual(mimetype2ext('text/vtt'), 'vtt')
        self.assertEqual(mimetype2ext('text/vtt;charset=utf-8'), 'vtt')
        self.assertEqual(mimetype2ext('text/html; charset=utf-8'), 'html')
        self.assertEqual(mimetype2ext('audio/x-wav'), 'wav')
        self.assertEqual(mimetype2ext('audio/x-wav;codec=pcm'), 'wav')

    def test_month_by_name(self):
        self.assertEqual(month_by_name(None), None)
        self.assertEqual(month_by_name('December', 'en'), 12)
        self.assertEqual(month_by_name('décembre', 'fr'), 12)
        self.assertEqual(month_by_name('December'), 12)
        self.assertEqual(month_by_name('décembre'), None)
        self.assertEqual(month_by_name('Unknown', 'unknown'), None)

    def test_parse_codecs(self):
        self.assertEqual(parse_codecs(''), {})
        self.assertEqual(parse_codecs('avc1.77.30, mp4a.40.2'), {
            'vcodec': 'avc1.77.30',
            'acodec': 'mp4a.40.2',
            'dynamic_range': None,
        })
        self.assertEqual(parse_codecs('mp4a.40.2'), {
            'vcodec': 'none',
            'acodec': 'mp4a.40.2',
            'dynamic_range': None,
        })
        self.assertEqual(parse_codecs('mp4a.40.5,avc1.42001e'), {
            'vcodec': 'avc1.42001e',
            'acodec': 'mp4a.40.5',
            'dynamic_range': None,
        })
        self.assertEqual(parse_codecs('avc3.640028'), {
            'vcodec': 'avc3.640028',
            'acodec': 'none',
            'dynamic_range': None,
        })
        self.assertEqual(parse_codecs(', h264,,newcodec,aac'), {
            'vcodec': 'h264',
            'acodec': 'aac',
            'dynamic_range': None,
        })
        self.assertEqual(parse_codecs('av01.0.05M.08'), {
            'vcodec': 'av01.0.05M.08',
            'acodec': 'none',
            'dynamic_range': None,
        })
        self.assertEqual(parse_codecs('vp9.2'), {
            'vcodec': 'vp9.2',
            'acodec': 'none',
            'dynamic_range': 'HDR10',
        })
        self.assertEqual(parse_codecs('av01.0.12M.10.0.110.09.16.09.0'), {
            'vcodec': 'av01.0.12M.10.0.110.09.16.09.0',
            'acodec': 'none',
            'dynamic_range': 'HDR10',
        })
        self.assertEqual(parse_codecs('dvhe'), {
            'vcodec': 'dvhe',
            'acodec': 'none',
            'dynamic_range': 'DV',
        })
        self.assertEqual(parse_codecs('fLaC'), {
            'vcodec': 'none',
            'acodec': 'flac',
            'dynamic_range': None,
        })
        self.assertEqual(parse_codecs('theora, vorbis'), {
            'vcodec': 'theora',
            'acodec': 'vorbis',
            'dynamic_range': None,
        })
        self.assertEqual(parse_codecs('unknownvcodec, unknownacodec'), {
            'vcodec': 'unknownvcodec',
            'acodec': 'unknownacodec',
        })
        self.assertEqual(parse_codecs('unknown'), {})

    def test_escape_rfc3986(self):
        reserved = "!*'();:@&=+$,/?#[]"
        unreserved = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~'
        self.assertEqual(escape_rfc3986(reserved), reserved)
        self.assertEqual(escape_rfc3986(unreserved), unreserved)
        self.assertEqual(escape_rfc3986('тест'), '%D1%82%D0%B5%D1%81%D1%82')
        self.assertEqual(escape_rfc3986('%D1%82%D0%B5%D1%81%D1%82'), '%D1%82%D0%B5%D1%81%D1%82')
        self.assertEqual(escape_rfc3986('foo bar'), 'foo%20bar')
        self.assertEqual(escape_rfc3986('foo%20bar'), 'foo%20bar')

    def test_normalize_url(self):
        self.assertEqual(
            normalize_url('http://wowza.imust.org/srv/vod/telemb/new/UPLOAD/UPLOAD/20224_IncendieHavré_FD.mp4'),
            'http://wowza.imust.org/srv/vod/telemb/new/UPLOAD/UPLOAD/20224_IncendieHavre%CC%81_FD.mp4',
        )
        self.assertEqual(
            normalize_url('http://www.ardmediathek.de/tv/Sturm-der-Liebe/Folge-2036-Zu-Mann-und-Frau-erklärt/Das-Erste/Video?documentId=22673108&bcastId=5290'),
            'http://www.ardmediathek.de/tv/Sturm-der-Liebe/Folge-2036-Zu-Mann-und-Frau-erkl%C3%A4rt/Das-Erste/Video?documentId=22673108&bcastId=5290',
        )
        self.assertEqual(
            normalize_url('http://тест.рф/фрагмент'),
            'http://xn--e1aybc.xn--p1ai/%D1%84%D1%80%D0%B0%D0%B3%D0%BC%D0%B5%D0%BD%D1%82',
        )
        self.assertEqual(
            normalize_url('http://тест.рф/абв?абв=абв#абв'),
            'http://xn--e1aybc.xn--p1ai/%D0%B0%D0%B1%D0%B2?%D0%B0%D0%B1%D0%B2=%D0%B0%D0%B1%D0%B2#%D0%B0%D0%B1%D0%B2',
        )
        self.assertEqual(normalize_url('http://vimeo.com/56015672#at=0'), 'http://vimeo.com/56015672#at=0')

        self.assertEqual(normalize_url('http://www.example.com/../a/b/../c/./d.html'), 'http://www.example.com/a/c/d.html')

    def test_remove_dot_segments(self):
        self.assertEqual(remove_dot_segments('/a/b/c/./../../g'), '/a/g')
        self.assertEqual(remove_dot_segments('mid/content=5/../6'), 'mid/6')
        self.assertEqual(remove_dot_segments('/ad/../cd'), '/cd')
        self.assertEqual(remove_dot_segments('/ad/../cd/'), '/cd/')
        self.assertEqual(remove_dot_segments('/..'), '/')
        self.assertEqual(remove_dot_segments('/./'), '/')
        self.assertEqual(remove_dot_segments('/./a'), '/a')
        self.assertEqual(remove_dot_segments('/abc/./.././d/././e/.././f/./../../ghi'), '/ghi')
        self.assertEqual(remove_dot_segments('/'), '/')
        self.assertEqual(remove_dot_segments('/t'), '/t')
        self.assertEqual(remove_dot_segments('t'), 't')
        self.assertEqual(remove_dot_segments(''), '')
        self.assertEqual(remove_dot_segments('/../a/b/c'), '/a/b/c')
        self.assertEqual(remove_dot_segments('../a'), 'a')
        self.assertEqual(remove_dot_segments('./a'), 'a')
        self.assertEqual(remove_dot_segments('.'), '')
        self.assertEqual(remove_dot_segments('////'), '////')

    def test_js_to_json_vars_strings(self):
        self.assertDictEqual(
            json.loads(js_to_json(
                '''{
                    'null': a,
                    'nullStr': b,
                    'true': c,
                    'trueStr': d,
                    'false': e,
                    'falseStr': f,
                    'unresolvedVar': g,
                }''',
                {
                    'a': 'null',
                    'b': '"null"',
                    'c': 'true',
                    'd': '"true"',
                    'e': 'false',
                    'f': '"false"',
                    'g': 'var',
                },
            )),
            {
                'null': None,
                'nullStr': 'null',
                'true': True,
                'trueStr': 'true',
                'false': False,
                'falseStr': 'false',
                'unresolvedVar': 'var',
            },
        )

        self.assertDictEqual(
            json.loads(js_to_json(
                '''{
                    'int': a,
                    'intStr': b,
                    'float': c,
                    'floatStr': d,
                }''',
                {
                    'a': '123',
                    'b': '"123"',
                    'c': '1.23',
                    'd': '"1.23"',
                },
            )),
            {
                'int': 123,
                'intStr': '123',
                'float': 1.23,
                'floatStr': '1.23',
            },
        )

        self.assertDictEqual(
            json.loads(js_to_json(
                '''{
                    'object': a,
                    'objectStr': b,
                    'array': c,
                    'arrayStr': d,
                }''',
                {
                    'a': '{}',
                    'b': '"{}"',
                    'c': '[]',
                    'd': '"[]"',
                },
            )),
            {
                'object': {},
                'objectStr': '{}',
                'array': [],
                'arrayStr': '[]',
            },
        )

    def test_js_to_json_realworld(self):
        inp = '''{
            'clip':{'provider':'pseudo'}
        }'''
        self.assertEqual(js_to_json(inp), '''{
            "clip":{"provider":"pseudo"}
        }''')
        json.loads(js_to_json(inp))

        inp = '''{
            'playlist':[{'controls':{'all':null}}]
        }'''
        self.assertEqual(js_to_json(inp), '''{
            "playlist":[{"controls":{"all":null}}]
        }''')

        inp = '''"The CW\\'s \\'Crazy Ex-Girlfriend\\'"'''
        self.assertEqual(js_to_json(inp), '''"The CW's 'Crazy Ex-Girlfriend'"''')

        inp = '"SAND Number: SAND 2013-7800P\\nPresenter: Tom Russo\\nHabanero Software Training - Xyce Software\\nXyce, Sandia\\u0027s"'
        json_code = js_to_json(inp)
        self.assertEqual(json.loads(json_code), json.loads(inp))

        inp = '''{
            0:{src:'skipped', type: 'application/dash+xml'},
            1:{src:'skipped', type: 'application/vnd.apple.mpegURL'},
        }'''
        self.assertEqual(js_to_json(inp), '''{
            "0":{"src":"skipped", "type": "application/dash+xml"},
            "1":{"src":"skipped", "type": "application/vnd.apple.mpegURL"}
        }''')

        inp = '''{"foo":101}'''
        self.assertEqual(js_to_json(inp), '''{"foo":101}''')

        inp = '''{"duration": "00:01:07"}'''
        self.assertEqual(js_to_json(inp), '''{"duration": "00:01:07"}''')

        inp = '''{segments: [{"offset":-3.885780586188048e-16,"duration":39.75000000000001}]}'''
        self.assertEqual(js_to_json(inp), '''{"segments": [{"offset":-3.885780586188048e-16,"duration":39.75000000000001}]}''')

    def test_js_to_json_edgecases(self):
        on = js_to_json("{abc_def:'1\\'\\\\2\\\\\\'3\"4'}")
        self.assertEqual(json.loads(on), {'abc_def': "1'\\2\\'3\"4"})

        on = js_to_json('{"abc": true}')
        self.assertEqual(json.loads(on), {'abc': True})

        # Ignore JavaScript code as well
        on = js_to_json('''{
            "x": 1,
            y: "a",
            z: some.code
        }''')
        d = json.loads(on)
        self.assertEqual(d['x'], 1)
        self.assertEqual(d['y'], 'a')

        # Just drop ! prefix for now though this results in a wrong value
        on = js_to_json('''{
            a: !0,
            b: !1,
            c: !!0,
            d: !!42.42,
            e: !!![],
            f: !"abc",
            g: !"",
            !42: 42
        }''')
        self.assertEqual(json.loads(on), {
            'a': 0,
            'b': 1,
            'c': 0,
            'd': 42.42,
            'e': [],
            'f': 'abc',
            'g': '',
            '42': 42,
        })

        on = js_to_json('["abc", "def",]')
        self.assertEqual(json.loads(on), ['abc', 'def'])

        on = js_to_json('[/*comment\n*/"abc"/*comment\n*/,/*comment\n*/"def",/*comment\n*/]')
        self.assertEqual(json.loads(on), ['abc', 'def'])

        on = js_to_json('[//comment\n"abc" //comment\n,//comment\n"def",//comment\n]')
        self.assertEqual(json.loads(on), ['abc', 'def'])

        on = js_to_json('{"abc": "def",}')
        self.assertEqual(json.loads(on), {'abc': 'def'})

        on = js_to_json('{/*comment\n*/"abc"/*comment\n*/:/*comment\n*/"def"/*comment\n*/,/*comment\n*/}')
        self.assertEqual(json.loads(on), {'abc': 'def'})

        on = js_to_json('{ 0: /* " \n */ ",]" , }')
        self.assertEqual(json.loads(on), {'0': ',]'})

        on = js_to_json('{ /*comment\n*/0/*comment\n*/: /* " \n */ ",]" , }')
        self.assertEqual(json.loads(on), {'0': ',]'})

        on = js_to_json('{ 0: // comment\n1 }')
        self.assertEqual(json.loads(on), {'0': 1})

        on = js_to_json(r'["<p>x<\/p>"]')
        self.assertEqual(json.loads(on), ['<p>x</p>'])

        on = js_to_json(r'["\xaa"]')
        self.assertEqual(json.loads(on), ['\u00aa'])

        on = js_to_json("['a\\\nb']")
        self.assertEqual(json.loads(on), ['ab'])

        on = js_to_json("/*comment\n*/[/*comment\n*/'a\\\nb'/*comment\n*/]/*comment\n*/")
        self.assertEqual(json.loads(on), ['ab'])

        on = js_to_json('{0xff:0xff}')
        self.assertEqual(json.loads(on), {'255': 255})

        on = js_to_json('{/*comment\n*/0xff/*comment\n*/:/*comment\n*/0xff/*comment\n*/}')
        self.assertEqual(json.loads(on), {'255': 255})

        on = js_to_json('{077:077}')
        self.assertEqual(json.loads(on), {'63': 63})

        on = js_to_json('{/*comment\n*/077/*comment\n*/:/*comment\n*/077/*comment\n*/}')
        self.assertEqual(json.loads(on), {'63': 63})

        on = js_to_json('{42:42}')
        self.assertEqual(json.loads(on), {'42': 42})

        on = js_to_json('{/*comment\n*/42/*comment\n*/:/*comment\n*/42/*comment\n*/}')
        self.assertEqual(json.loads(on), {'42': 42})

        on = js_to_json('{42:4.2e1}')
        self.assertEqual(json.loads(on), {'42': 42.0})

        on = js_to_json('{ "0x40": "0x40" }')
        self.assertEqual(json.loads(on), {'0x40': '0x40'})

        on = js_to_json('{ "040": "040" }')
        self.assertEqual(json.loads(on), {'040': '040'})

        on = js_to_json('[1,//{},\n2]')
        self.assertEqual(json.loads(on), [1, 2])

        on = js_to_json(R'"\^\$\#"')
        self.assertEqual(json.loads(on), R'^$#', msg='Unnecessary escapes should be stripped')

        on = js_to_json('\'"\\""\'')
        self.assertEqual(json.loads(on), '"""', msg='Unnecessary quote escape should be escaped')

        on = js_to_json('[new Date("spam"), \'("eggs")\']')
        self.assertEqual(json.loads(on), ['spam', '("eggs")'], msg='Date regex should match a single string')

    def test_js_to_json_malformed(self):
        self.assertEqual(js_to_json('42a1'), '42"a1"')
        self.assertEqual(js_to_json('42a-1'), '42"a"-1')

    def test_js_to_json_template_literal(self):
        self.assertEqual(js_to_json('`Hello ${name}`', {'name': '"world"'}), '"Hello world"')
        self.assertEqual(js_to_json('`${name}${name}`', {'name': '"X"'}), '"XX"')
        self.assertEqual(js_to_json('`${name}${name}`', {'name': '5'}), '"55"')
        self.assertEqual(js_to_json('`${name}"${name}"`', {'name': '5'}), '"5\\"5\\""')
        self.assertEqual(js_to_json('`${name}`', {}), '"name"')

    def test_js_to_json_common_constructors(self):
        self.assertEqual(json.loads(js_to_json('new Map([["a", 5]])')), {'a': 5})
        self.assertEqual(json.loads(js_to_json('Array(5, 10)')), [5, 10])
        self.assertEqual(json.loads(js_to_json('new Array(15,5)')), [15, 5])
        self.assertEqual(json.loads(js_to_json('new Map([Array(5, 10),new Array(15,5)])')), {'5': 10, '15': 5})
        self.assertEqual(json.loads(js_to_json('new Date("123")')), '123')
        self.assertEqual(json.loads(js_to_json('new Date(\'2023-10-19\')')), '2023-10-19')

    def test_extract_attributes(self):
        self.assertEqual(extract_attributes('<e x="y">'), {'x': 'y'})
        self.assertEqual(extract_attributes("<e x='y'>"), {'x': 'y'})
        self.assertEqual(extract_attributes('<e x=y>'), {'x': 'y'})
        self.assertEqual(extract_attributes('<e x="a \'b\' c">'), {'x': "a 'b' c"})
        self.assertEqual(extract_attributes('<e x=\'a "b" c\'>'), {'x': 'a "b" c'})
        self.assertEqual(extract_attributes('<e x="&#121;">'), {'x': 'y'})
        self.assertEqual(extract_attributes('<e x="&#x79;">'), {'x': 'y'})
        self.assertEqual(extract_attributes('<e x="&amp;">'), {'x': '&'})  # XML
        self.assertEqual(extract_attributes('<e x="&quot;">'), {'x': '"'})
        self.assertEqual(extract_attributes('<e x="&pound;">'), {'x': '£'})  # HTML 3.2
        self.assertEqual(extract_attributes('<e x="&lambda;">'), {'x': 'λ'})  # HTML 4.0
        self.assertEqual(extract_attributes('<e x="&foo">'), {'x': '&foo'})
        self.assertEqual(extract_attributes('<e x="\'">'), {'x': "'"})
        self.assertEqual(extract_attributes('<e x=\'"\'>'), {'x': '"'})
        self.assertEqual(extract_attributes('<e x >'), {'x': None})
        self.assertEqual(extract_attributes('<e x=y a>'), {'x': 'y', 'a': None})
        self.assertEqual(extract_attributes('<e x= y>'), {'x': 'y'})
        self.assertEqual(extract_attributes('<e x=1 y=2 x=3>'), {'y': '2', 'x': '3'})
        self.assertEqual(extract_attributes('<e \nx=\ny\n>'), {'x': 'y'})
        self.assertEqual(extract_attributes('<e \nx=\n"y"\n>'), {'x': 'y'})
        self.assertEqual(extract_attributes("<e \nx=\n'y'\n>"), {'x': 'y'})
        self.assertEqual(extract_attributes('<e \nx="\ny\n">'), {'x': '\ny\n'})
        self.assertEqual(extract_attributes('<e CAPS=x>'), {'caps': 'x'})  # Names lowercased
        self.assertEqual(extract_attributes('<e x=1 X=2>'), {'x': '2'})
        self.assertEqual(extract_attributes('<e X=1 x=2>'), {'x': '2'})
        self.assertEqual(extract_attributes('<e _:funny-name1=1>'), {'_:funny-name1': '1'})
        self.assertEqual(extract_attributes('<e x="Fáilte 世界 \U0001f600">'), {'x': 'Fáilte 世界 \U0001f600'})
        self.assertEqual(extract_attributes('<e x="décompose&#769;">'), {'x': 'décompose\u0301'})
        # "Narrow" Python builds don't support unicode code points outside BMP.
        try:
            chr(0x10000)
            supports_outside_bmp = True
        except ValueError:
            supports_outside_bmp = False
        if supports_outside_bmp:
            self.assertEqual(extract_attributes('<e x="Smile &#128512;!">'), {'x': 'Smile \U0001f600!'})
        # Malformed HTML should not break attributes extraction on older Python
        self.assertEqual(extract_attributes('<mal"formed/>'), {})

    def test_clean_html(self):
        self.assertEqual(clean_html('a:\nb'), 'a: b')
        self.assertEqual(clean_html('a:\n   "b"'), 'a: "b"')
        self.assertEqual(clean_html('a<br>\xa0b'), 'a\nb')

    def test_intlist_to_bytes(self):
        self.assertEqual(
            intlist_to_bytes([0, 1, 127, 128, 255]),
            b'\x00\x01\x7f\x80\xff')

    def test_args_to_str(self):
        self.assertEqual(
            args_to_str(['foo', 'ba/r', '-baz', '2 be', '']),
            'foo ba/r -baz \'2 be\' \'\'' if compat_os_name != 'nt' else 'foo ba/r -baz "2 be" ""',
        )

    def test_parse_filesize(self):
        self.assertEqual(parse_filesize(None), None)
        self.assertEqual(parse_filesize(''), None)
        self.assertEqual(parse_filesize('91 B'), 91)
        self.assertEqual(parse_filesize('foobar'), None)
        self.assertEqual(parse_filesize('2 MiB'), 2097152)
        self.assertEqual(parse_filesize('5 GB'), 5000000000)
        self.assertEqual(parse_filesize('1.2Tb'), 1200000000000)
        self.assertEqual(parse_filesize('1.2tb'), 1200000000000)
        self.assertEqual(parse_filesize('1,24 KB'), 1240)
        self.assertEqual(parse_filesize('1,24 kb'), 1240)
        self.assertEqual(parse_filesize('8.5 megabytes'), 8500000)

    def test_parse_count(self):
        self.assertEqual(parse_count(None), None)
        self.assertEqual(parse_count(''), None)
        self.assertEqual(parse_count('0'), 0)
        self.assertEqual(parse_count('1000'), 1000)
        self.assertEqual(parse_count('1.000'), 1000)
        self.assertEqual(parse_count('1.1k'), 1100)
        self.assertEqual(parse_count('1.1 k'), 1100)
        self.assertEqual(parse_count('1,1 k'), 1100)
        self.assertEqual(parse_count('1.1kk'), 1100000)
        self.assertEqual(parse_count('1.1kk '), 1100000)
        self.assertEqual(parse_count('1,1kk'), 1100000)
        self.assertEqual(parse_count('100 views'), 100)
        self.assertEqual(parse_count('1,100 views'), 1100)
        self.assertEqual(parse_count('1.1kk views'), 1100000)
        self.assertEqual(parse_count('10M views'), 10000000)
        self.assertEqual(parse_count('has 10M views'), 10000000)

    def test_parse_resolution(self):
        self.assertEqual(parse_resolution(None), {})
        self.assertEqual(parse_resolution(''), {})
        self.assertEqual(parse_resolution(' 1920x1080'), {'width': 1920, 'height': 1080})
        self.assertEqual(parse_resolution('1920×1080 '), {'width': 1920, 'height': 1080})
        self.assertEqual(parse_resolution('1920 x 1080'), {'width': 1920, 'height': 1080})
        self.assertEqual(parse_resolution('720p'), {'height': 720})
        self.assertEqual(parse_resolution('4k'), {'height': 2160})
        self.assertEqual(parse_resolution('8K'), {'height': 4320})
        self.assertEqual(parse_resolution('pre_1920x1080_post'), {'width': 1920, 'height': 1080})
        self.assertEqual(parse_resolution('ep1x2'), {})
        self.assertEqual(parse_resolution('1920, 1080'), {'width': 1920, 'height': 1080})

    def test_parse_bitrate(self):
        self.assertEqual(parse_bitrate(None), None)
        self.assertEqual(parse_bitrate(''), None)
        self.assertEqual(parse_bitrate('300kbps'), 300)
        self.assertEqual(parse_bitrate('1500kbps'), 1500)
        self.assertEqual(parse_bitrate('300 kbps'), 300)

    def test_version_tuple(self):
        self.assertEqual(version_tuple('1'), (1,))
        self.assertEqual(version_tuple('10.23.344'), (10, 23, 344))
        self.assertEqual(version_tuple('10.1-6'), (10, 1, 6))  # avconv style

    def test_detect_exe_version(self):
        self.assertEqual(detect_exe_version('''ffmpeg version 1.2.1
built on May 27 2013 08:37:26 with gcc 4.7 (Debian 4.7.3-4)
configuration: --prefix=/usr --extra-'''), '1.2.1')
        self.assertEqual(detect_exe_version('''ffmpeg version N-63176-g1fb4685
built on May 15 2014 22:09:06 with gcc 4.8.2 (GCC)'''), 'N-63176-g1fb4685')
        self.assertEqual(detect_exe_version('''X server found. dri2 connection failed!
Trying to open render node...
Success at /dev/dri/renderD128.
ffmpeg version 2.4.4 Copyright (c) 2000-2014 the FFmpeg ...'''), '2.4.4')

    def test_age_restricted(self):
        self.assertFalse(age_restricted(None, 10))  # unrestricted content
        self.assertFalse(age_restricted(1, None))  # unrestricted policy
        self.assertFalse(age_restricted(8, 10))
        self.assertTrue(age_restricted(18, 14))
        self.assertFalse(age_restricted(18, 18))

    def test_is_html(self):
        self.assertFalse(is_html(b'\x49\x44\x43<html'))
        self.assertTrue(is_html(b'<!DOCTYPE foo>\xaaa'))
        self.assertTrue(is_html(  # UTF-8 with BOM
            b'\xef\xbb\xbf<!DOCTYPE foo>\xaaa'))
        self.assertTrue(is_html(  # UTF-16-LE
            b'\xff\xfe<\x00h\x00t\x00m\x00l\x00>\x00\xe4\x00',
        ))
        self.assertTrue(is_html(  # UTF-16-BE
            b'\xfe\xff\x00<\x00h\x00t\x00m\x00l\x00>\x00\xe4',
        ))
        self.assertTrue(is_html(  # UTF-32-BE
            b'\x00\x00\xFE\xFF\x00\x00\x00<\x00\x00\x00h\x00\x00\x00t\x00\x00\x00m\x00\x00\x00l\x00\x00\x00>\x00\x00\x00\xe4'))
        self.assertTrue(is_html(  # UTF-32-LE
            b'\xFF\xFE\x00\x00<\x00\x00\x00h\x00\x00\x00t\x00\x00\x00m\x00\x00\x00l\x00\x00\x00>\x00\x00\x00\xe4\x00\x00\x00'))

    def test_render_table(self):
        self.assertEqual(
            render_table(
                ['a', 'empty', 'bcd'],
                [[123, '', 4], [9999, '', 51]]),
            'a    empty bcd\n'
            '123        4\n'
            '9999       51')

        self.assertEqual(
            render_table(
                ['a', 'empty', 'bcd'],
                [[123, '', 4], [9999, '', 51]],
                hide_empty=True),
            'a    bcd\n'
            '123  4\n'
            '9999 51')

        self.assertEqual(
            render_table(
                ['\ta', 'bcd'],
                [['1\t23', 4], ['\t9999', 51]]),
            '   a bcd\n'
            '1 23 4\n'
            '9999 51')

        self.assertEqual(
            render_table(
                ['a', 'bcd'],
                [[123, 4], [9999, 51]],
                delim='-'),
            'a    bcd\n'
            '--------\n'
            '123  4\n'
            '9999 51')

        self.assertEqual(
            render_table(
                ['a', 'bcd'],
                [[123, 4], [9999, 51]],
                delim='-', extra_gap=2),
            'a      bcd\n'
            '----------\n'
            '123    4\n'
            '9999   51')

    def test_match_str(self):
        # Unary
        self.assertFalse(match_str('xy', {'x': 1200}))
        self.assertTrue(match_str('!xy', {'x': 1200}))
        self.assertTrue(match_str('x', {'x': 1200}))
        self.assertFalse(match_str('!x', {'x': 1200}))
        self.assertTrue(match_str('x', {'x': 0}))
        self.assertTrue(match_str('is_live', {'is_live': True}))
        self.assertFalse(match_str('is_live', {'is_live': False}))
        self.assertFalse(match_str('is_live', {'is_live': None}))
        self.assertFalse(match_str('is_live', {}))
        self.assertFalse(match_str('!is_live', {'is_live': True}))
        self.assertTrue(match_str('!is_live', {'is_live': False}))
        self.assertTrue(match_str('!is_live', {'is_live': None}))
        self.assertTrue(match_str('!is_live', {}))
        self.assertTrue(match_str('title', {'title': 'abc'}))
        self.assertTrue(match_str('title', {'title': ''}))
        self.assertFalse(match_str('!title', {'title': 'abc'}))
        self.assertFalse(match_str('!title', {'title': ''}))

        # Numeric
        self.assertFalse(match_str('x>0', {'x': 0}))
        self.assertFalse(match_str('x>0', {}))
        self.assertTrue(match_str('x>?0', {}))
        self.assertTrue(match_str('x>1K', {'x': 1200}))
        self.assertFalse(match_str('x>2K', {'x': 1200}))
        self.assertTrue(match_str('x>=1200 & x < 1300', {'x': 1200}))
        self.assertFalse(match_str('x>=1100 & x < 1200', {'x': 1200}))
        self.assertTrue(match_str('x > 1:0:0', {'x': 3700}))

        # String
        self.assertFalse(match_str('y=a212', {'y': 'foobar42'}))
        self.assertTrue(match_str('y=foobar42', {'y': 'foobar42'}))
        self.assertFalse(match_str('y!=foobar42', {'y': 'foobar42'}))
        self.assertTrue(match_str('y!=foobar2', {'y': 'foobar42'}))
        self.assertTrue(match_str('y^=foo', {'y': 'foobar42'}))
        self.assertFalse(match_str('y!^=foo', {'y': 'foobar42'}))
        self.assertFalse(match_str('y^=bar', {'y': 'foobar42'}))
        self.assertTrue(match_str('y!^=bar', {'y': 'foobar42'}))
        self.assertRaises(ValueError, match_str, 'x^=42', {'x': 42})
        self.assertTrue(match_str('y*=bar', {'y': 'foobar42'}))
        self.assertFalse(match_str('y!*=bar', {'y': 'foobar42'}))
        self.assertFalse(match_str('y*=baz', {'y': 'foobar42'}))
        self.assertTrue(match_str('y!*=baz', {'y': 'foobar42'}))
        self.assertTrue(match_str('y$=42', {'y': 'foobar42'}))
        self.assertFalse(match_str('y$=43', {'y': 'foobar42'}))

        # And
        self.assertFalse(match_str(
            'like_count > 100 & dislike_count <? 50 & description',
            {'like_count': 90, 'description': 'foo'}))
        self.assertTrue(match_str(
            'like_count > 100 & dislike_count <? 50 & description',
            {'like_count': 190, 'description': 'foo'}))
        self.assertFalse(match_str(
            'like_count > 100 & dislike_count <? 50 & description',
            {'like_count': 190, 'dislike_count': 60, 'description': 'foo'}))
        self.assertFalse(match_str(
            'like_count > 100 & dislike_count <? 50 & description',
            {'like_count': 190, 'dislike_count': 10}))

        # Regex
        self.assertTrue(match_str(r'x~=\bbar', {'x': 'foo bar'}))
        self.assertFalse(match_str(r'x~=\bbar.+', {'x': 'foo bar'}))
        self.assertFalse(match_str(r'x~=^FOO', {'x': 'foo bar'}))
        self.assertTrue(match_str(r'x~=(?i)^FOO', {'x': 'foo bar'}))

        # Quotes
        self.assertTrue(match_str(r'x^="foo"', {'x': 'foo "bar"'}))
        self.assertFalse(match_str(r'x^="foo  "', {'x': 'foo "bar"'}))
        self.assertFalse(match_str(r'x$="bar"', {'x': 'foo "bar"'}))
        self.assertTrue(match_str(r'x$=" \"bar\""', {'x': 'foo "bar"'}))

        # Escaping &
        self.assertFalse(match_str(r'x=foo & bar', {'x': 'foo & bar'}))
        self.assertTrue(match_str(r'x=foo \& bar', {'x': 'foo & bar'}))
        self.assertTrue(match_str(r'x=foo \& bar & x^=foo', {'x': 'foo & bar'}))
        self.assertTrue(match_str(r'x="foo \& bar" & x^=foo', {'x': 'foo & bar'}))

        # Example from docs
        self.assertTrue(match_str(
            r"!is_live & like_count>?100 & description~='(?i)\bcats \& dogs\b'",
            {'description': 'Raining Cats & Dogs'}))

        # Incomplete
        self.assertFalse(match_str('id!=foo', {'id': 'foo'}, True))
        self.assertTrue(match_str('x', {'id': 'foo'}, True))
        self.assertTrue(match_str('!x', {'id': 'foo'}, True))
        self.assertFalse(match_str('x', {'id': 'foo'}, False))

    def test_parse_dfxp_time_expr(self):
        self.assertEqual(parse_dfxp_time_expr(None), None)
        self.assertEqual(parse_dfxp_time_expr(''), None)
        self.assertEqual(parse_dfxp_time_expr('0.1'), 0.1)
        self.assertEqual(parse_dfxp_time_expr('0.1s'), 0.1)
        self.assertEqual(parse_dfxp_time_expr('00:00:01'), 1.0)
        self.assertEqual(parse_dfxp_time_expr('00:00:01.100'), 1.1)
        self.assertEqual(parse_dfxp_time_expr('00:00:01:100'), 1.1)

    def test_dfxp2srt(self):
        dfxp_data = '''<?xml version="1.0" encoding="UTF-8"?>
            <tt xmlns="http://www.w3.org/ns/ttml" xml:lang="en" xmlns:tts="http://www.w3.org/ns/ttml#parameter">
            <body>
                <div xml:lang="en">
                    <p begin="0" end="1">The following line contains Chinese characters and special symbols</p>
                    <p begin="1" end="2">第二行<br/>♪♪</p>
                    <p begin="2" dur="1"><span>Third<br/>Line</span></p>
                    <p begin="3" end="-1">Lines with invalid timestamps are ignored</p>
                    <p begin="-1" end="-1">Ignore, two</p>
                    <p begin="3" dur="-1">Ignored, three</p>
                </div>
            </body>
            </tt>'''.encode()
        srt_data = '''1
00:00:00,000 --> 00:00:01,000
The following line contains Chinese characters and special symbols

2
00:00:01,000 --> 00:00:02,000
第二行
♪♪

3
00:00:02,000 --> 00:00:03,000
Third
Line

'''
        self.assertEqual(dfxp2srt(dfxp_data), srt_data)

        dfxp_data_no_default_namespace = b'''<?xml version="1.0" encoding="UTF-8"?>
            <tt xml:lang="en" xmlns:tts="http://www.w3.org/ns/ttml#parameter">
            <body>
                <div xml:lang="en">
                    <p begin="0" end="1">The first line</p>
                </div>
            </body>
            </tt>'''
        srt_data = '''1
00:00:00,000 --> 00:00:01,000
The first line

'''
        self.assertEqual(dfxp2srt(dfxp_data_no_default_namespace), srt_data)

        dfxp_data_with_style = b'''<?xml version="1.0" encoding="utf-8"?>
<tt xmlns="http://www.w3.org/2006/10/ttaf1" xmlns:ttp="http://www.w3.org/2006/10/ttaf1#parameter" ttp:timeBase="media" xmlns:tts="http://www.w3.org/2006/10/ttaf1#style" xml:lang="en" xmlns:ttm="http://www.w3.org/2006/10/ttaf1#metadata">
  <head>
    <styling>
      <style id="s2" style="s0" tts:color="cyan" tts:fontWeight="bold" />
      <style id="s1" style="s0" tts:color="yellow" tts:fontStyle="italic" />
      <style id="s3" style="s0" tts:color="lime" tts:textDecoration="underline" />
      <style id="s0" tts:backgroundColor="black" tts:fontStyle="normal" tts:fontSize="16" tts:fontFamily="sansSerif" tts:color="white" />
    </styling>
  </head>
  <body tts:textAlign="center" style="s0">
    <div>
      <p begin="00:00:02.08" id="p0" end="00:00:05.84">default style<span tts:color="red">custom style</span></p>
      <p style="s2" begin="00:00:02.08" id="p0" end="00:00:05.84"><span tts:color="lime">part 1<br /></span><span tts:color="cyan">part 2</span></p>
      <p style="s3" begin="00:00:05.84" id="p1" end="00:00:09.56">line 3<br />part 3</p>
      <p style="s1" tts:textDecoration="underline" begin="00:00:09.56" id="p2" end="00:00:12.36"><span style="s2" tts:color="lime">inner<br /> </span>style</p>
    </div>
  </body>
</tt>'''
        srt_data = '''1
00:00:02,080 --> 00:00:05,840
<font color="white" face="sansSerif" size="16">default style<font color="red">custom style</font></font>

2
00:00:02,080 --> 00:00:05,840
<b><font color="cyan" face="sansSerif" size="16"><font color="lime">part 1
</font>part 2</font></b>

3
00:00:05,840 --> 00:00:09,560
<u><font color="lime">line 3
part 3</font></u>

4
00:00:09,560 --> 00:00:12,360
<i><u><font color="yellow"><font color="lime">inner
 </font>style</font></u></i>

'''
        self.assertEqual(dfxp2srt(dfxp_data_with_style), srt_data)

        dfxp_data_non_utf8 = '''<?xml version="1.0" encoding="UTF-16"?>
            <tt xmlns="http://www.w3.org/ns/ttml" xml:lang="en" xmlns:tts="http://www.w3.org/ns/ttml#parameter">
            <body>
                <div xml:lang="en">
                    <p begin="0" end="1">Line 1</p>
                    <p begin="1" end="2">第二行</p>
                </div>
            </body>
            </tt>'''.encode('utf-16')
        srt_data = '''1
00:00:00,000 --> 00:00:01,000
Line 1

2
00:00:01,000 --> 00:00:02,000
第二行

'''
        self.assertEqual(dfxp2srt(dfxp_data_non_utf8), srt_data)

    def test_cli_option(self):
        self.assertEqual(cli_option({'proxy': '127.0.0.1:3128'}, '--proxy', 'proxy'), ['--proxy', '127.0.0.1:3128'])
        self.assertEqual(cli_option({'proxy': None}, '--proxy', 'proxy'), [])
        self.assertEqual(cli_option({}, '--proxy', 'proxy'), [])
        self.assertEqual(cli_option({'retries': 10}, '--retries', 'retries'), ['--retries', '10'])

    def test_cli_valueless_option(self):
        self.assertEqual(cli_valueless_option(
            {'downloader': 'external'}, '--external-downloader', 'downloader', 'external'), ['--external-downloader'])
        self.assertEqual(cli_valueless_option(
            {'downloader': 'internal'}, '--external-downloader', 'downloader', 'external'), [])
        self.assertEqual(cli_valueless_option(
            {'nocheckcertificate': True}, '--no-check-certificate', 'nocheckcertificate'), ['--no-check-certificate'])
        self.assertEqual(cli_valueless_option(
            {'nocheckcertificate': False}, '--no-check-certificate', 'nocheckcertificate'), [])
        self.assertEqual(cli_valueless_option(
            {'checkcertificate': True}, '--no-check-certificate', 'checkcertificate', False), [])
        self.assertEqual(cli_valueless_option(
            {'checkcertificate': False}, '--no-check-certificate', 'checkcertificate', False), ['--no-check-certificate'])

    def test_cli_bool_option(self):
        self.assertEqual(
            cli_bool_option(
                {'nocheckcertificate': True}, '--no-check-certificate', 'nocheckcertificate'),
            ['--no-check-certificate', 'true'])
        self.assertEqual(
            cli_bool_option(
                {'nocheckcertificate': True}, '--no-check-certificate', 'nocheckcertificate', separator='='),
            ['--no-check-certificate=true'])
        self.assertEqual(
            cli_bool_option(
                {'nocheckcertificate': True}, '--check-certificate', 'nocheckcertificate', 'false', 'true'),
            ['--check-certificate', 'false'])
        self.assertEqual(
            cli_bool_option(
                {'nocheckcertificate': True}, '--check-certificate', 'nocheckcertificate', 'false', 'true', '='),
            ['--check-certificate=false'])
        self.assertEqual(
            cli_bool_option(
                {'nocheckcertificate': False}, '--check-certificate', 'nocheckcertificate', 'false', 'true'),
            ['--check-certificate', 'true'])
        self.assertEqual(
            cli_bool_option(
                {'nocheckcertificate': False}, '--check-certificate', 'nocheckcertificate', 'false', 'true', '='),
            ['--check-certificate=true'])
        self.assertEqual(
            cli_bool_option(
                {}, '--check-certificate', 'nocheckcertificate', 'false', 'true', '='),
            [])

    def test_ohdave_rsa_encrypt(self):
        N = 0xab86b6371b5318aaa1d3c9e612a9f1264f372323c8c0f19875b5fc3b3fd3afcc1e5bec527aa94bfa85bffc157e4245aebda05389a5357b75115ac94f074aefcd
        e = 65537

        self.assertEqual(
            ohdave_rsa_encrypt(b'aa111222', e, N),
            '726664bd9a23fd0c70f9f1b84aab5e3905ce1e45a584e9cbcf9bcc7510338fc1986d6c599ff990d923aa43c51c0d9013cd572e13bc58f4ae48f2ed8c0b0ba881')

    def test_pkcs1pad(self):
        data = [1, 2, 3]
        padded_data = pkcs1pad(data, 32)
        self.assertEqual(padded_data[:2], [0, 2])
        self.assertEqual(padded_data[28:], [0, 1, 2, 3])

        self.assertRaises(ValueError, pkcs1pad, data, 8)

    def test_encode_base_n(self):
        self.assertEqual(encode_base_n(0, 30), '0')
        self.assertEqual(encode_base_n(80, 30), '2k')

        custom_table = '9876543210ZYXWVUTSRQPONMLKJIHGFEDCBA'
        self.assertEqual(encode_base_n(0, 30, custom_table), '9')
        self.assertEqual(encode_base_n(80, 30, custom_table), '7P')

        self.assertRaises(ValueError, encode_base_n, 0, 70)
        self.assertRaises(ValueError, encode_base_n, 0, 60, custom_table)

    def test_caesar(self):
        self.assertEqual(caesar('ace', 'abcdef', 2), 'cea')
        self.assertEqual(caesar('cea', 'abcdef', -2), 'ace')
        self.assertEqual(caesar('ace', 'abcdef', -2), 'eac')
        self.assertEqual(caesar('eac', 'abcdef', 2), 'ace')
        self.assertEqual(caesar('ace', 'abcdef', 0), 'ace')
        self.assertEqual(caesar('xyz', 'abcdef', 2), 'xyz')
        self.assertEqual(caesar('abc', 'acegik', 2), 'ebg')
        self.assertEqual(caesar('ebg', 'acegik', -2), 'abc')

    def test_rot47(self):
        self.assertEqual(rot47('yt-dlp'), r'JE\5=A')
        self.assertEqual(rot47('YT-DLP'), r'*%\s{!')

    def test_urshift(self):
        self.assertEqual(urshift(3, 1), 1)
        self.assertEqual(urshift(-3, 1), 2147483646)

    GET_ELEMENT_BY_CLASS_TEST_STRING = '''
        <span class="foo bar">nice</span>
    '''

    def test_get_element_by_class(self):
        html = self.GET_ELEMENT_BY_CLASS_TEST_STRING

        self.assertEqual(get_element_by_class('foo', html), 'nice')
        self.assertEqual(get_element_by_class('no-such-class', html), None)

    def test_get_element_html_by_class(self):
        html = self.GET_ELEMENT_BY_CLASS_TEST_STRING

        self.assertEqual(get_element_html_by_class('foo', html), html.strip())
        self.assertEqual(get_element_by_class('no-such-class', html), None)

    GET_ELEMENT_BY_ATTRIBUTE_TEST_STRING = '''
        <div itemprop="author" itemscope>foo</div>
    '''

    def test_get_element_by_attribute(self):
        html = self.GET_ELEMENT_BY_CLASS_TEST_STRING

        self.assertEqual(get_element_by_attribute('class', 'foo bar', html), 'nice')
        self.assertEqual(get_element_by_attribute('class', 'foo', html), None)
        self.assertEqual(get_element_by_attribute('class', 'no-such-foo', html), None)

        html = self.GET_ELEMENT_BY_ATTRIBUTE_TEST_STRING

        self.assertEqual(get_element_by_attribute('itemprop', 'author', html), 'foo')

    def test_get_element_html_by_attribute(self):
        html = self.GET_ELEMENT_BY_CLASS_TEST_STRING

        self.assertEqual(get_element_html_by_attribute('class', 'foo bar', html), html.strip())
        self.assertEqual(get_element_html_by_attribute('class', 'foo', html), None)
        self.assertEqual(get_element_html_by_attribute('class', 'no-such-foo', html), None)

        html = self.GET_ELEMENT_BY_ATTRIBUTE_TEST_STRING

        self.assertEqual(get_element_html_by_attribute('itemprop', 'author', html), html.strip())

    GET_ELEMENTS_BY_CLASS_TEST_STRING = '''
        <span class="foo bar">nice</span><span class="foo bar">also nice</span>
    '''
    GET_ELEMENTS_BY_CLASS_RES = ['<span class="foo bar">nice</span>', '<span class="foo bar">also nice</span>']

    def test_get_elements_by_class(self):
        html = self.GET_ELEMENTS_BY_CLASS_TEST_STRING

        self.assertEqual(get_elements_by_class('foo', html), ['nice', 'also nice'])
        self.assertEqual(get_elements_by_class('no-such-class', html), [])

    def test_get_elements_html_by_class(self):
        html = self.GET_ELEMENTS_BY_CLASS_TEST_STRING

        self.assertEqual(get_elements_html_by_class('foo', html), self.GET_ELEMENTS_BY_CLASS_RES)
        self.assertEqual(get_elements_html_by_class('no-such-class', html), [])

    def test_get_elements_by_attribute(self):
        html = self.GET_ELEMENTS_BY_CLASS_TEST_STRING

        self.assertEqual(get_elements_by_attribute('class', 'foo bar', html), ['nice', 'also nice'])
        self.assertEqual(get_elements_by_attribute('class', 'foo', html), [])
        self.assertEqual(get_elements_by_attribute('class', 'no-such-foo', html), [])

    def test_get_elements_html_by_attribute(self):
        html = self.GET_ELEMENTS_BY_CLASS_TEST_STRING

        self.assertEqual(get_elements_html_by_attribute('class', 'foo bar', html), self.GET_ELEMENTS_BY_CLASS_RES)
        self.assertEqual(get_elements_html_by_attribute('class', 'foo', html), [])
        self.assertEqual(get_elements_html_by_attribute('class', 'no-such-foo', html), [])

    def test_get_elements_text_and_html_by_attribute(self):
        html = self.GET_ELEMENTS_BY_CLASS_TEST_STRING

        self.assertEqual(
            list(get_elements_text_and_html_by_attribute('class', 'foo bar', html)),
            list(zip(['nice', 'also nice'], self.GET_ELEMENTS_BY_CLASS_RES)))
        self.assertEqual(list(get_elements_text_and_html_by_attribute('class', 'foo', html)), [])
        self.assertEqual(list(get_elements_text_and_html_by_attribute('class', 'no-such-foo', html)), [])

        self.assertEqual(list(get_elements_text_and_html_by_attribute(
            'class', 'foo', '<a class="foo">nice</a><span class="foo">nice</span>', tag='a')), [('nice', '<a class="foo">nice</a>')])

    GET_ELEMENT_BY_TAG_TEST_STRING = '''
    random text lorem ipsum</p>
    <div>
        this should be returned
        <span>this should also be returned</span>
        <div>
            this should also be returned
        </div>
        closing tag above should not trick, so this should also be returned
    </div>
    but this text should not be returned
    '''
    GET_ELEMENT_BY_TAG_RES_OUTERDIV_HTML = GET_ELEMENT_BY_TAG_TEST_STRING.strip()[32:276]
    GET_ELEMENT_BY_TAG_RES_OUTERDIV_TEXT = GET_ELEMENT_BY_TAG_RES_OUTERDIV_HTML[5:-6]
    GET_ELEMENT_BY_TAG_RES_INNERSPAN_HTML = GET_ELEMENT_BY_TAG_TEST_STRING.strip()[78:119]
    GET_ELEMENT_BY_TAG_RES_INNERSPAN_TEXT = GET_ELEMENT_BY_TAG_RES_INNERSPAN_HTML[6:-7]

    def test_get_element_text_and_html_by_tag(self):
        html = self.GET_ELEMENT_BY_TAG_TEST_STRING

        self.assertEqual(
            get_element_text_and_html_by_tag('div', html),
            (self.GET_ELEMENT_BY_TAG_RES_OUTERDIV_TEXT, self.GET_ELEMENT_BY_TAG_RES_OUTERDIV_HTML))
        self.assertEqual(
            get_element_text_and_html_by_tag('span', html),
            (self.GET_ELEMENT_BY_TAG_RES_INNERSPAN_TEXT, self.GET_ELEMENT_BY_TAG_RES_INNERSPAN_HTML))
        self.assertRaises(compat_HTMLParseError, get_element_text_and_html_by_tag, 'article', html)

    def test_iri_to_uri(self):
        self.assertEqual(
            iri_to_uri('https://www.google.com/search?q=foo&ie=utf-8&oe=utf-8&client=firefox-b'),
            'https://www.google.com/search?q=foo&ie=utf-8&oe=utf-8&client=firefox-b')  # Same
        self.assertEqual(
            iri_to_uri('https://www.google.com/search?q=Käsesoßenrührlöffel'),  # German for cheese sauce stirring spoon
            'https://www.google.com/search?q=K%C3%A4seso%C3%9Fenr%C3%BChrl%C3%B6ffel')
        self.assertEqual(
            iri_to_uri('https://www.google.com/search?q=lt<+gt>+eq%3D+amp%26+percent%25+hash%23+colon%3A+tilde~#trash=?&garbage=#'),
            'https://www.google.com/search?q=lt%3C+gt%3E+eq%3D+amp%26+percent%25+hash%23+colon%3A+tilde~#trash=?&garbage=#')
        self.assertEqual(
            iri_to_uri('http://правозащита38.рф/category/news/'),
            'http://xn--38-6kcaak9aj5chl4a3g.xn--p1ai/category/news/')
        self.assertEqual(
            iri_to_uri('http://www.правозащита38.рф/category/news/'),
            'http://www.xn--38-6kcaak9aj5chl4a3g.xn--p1ai/category/news/')
        self.assertEqual(
            iri_to_uri('https://i❤.ws/emojidomain/👍👏🤝💪'),
            'https://xn--i-7iq.ws/emojidomain/%F0%9F%91%8D%F0%9F%91%8F%F0%9F%A4%9D%F0%9F%92%AA')
        self.assertEqual(
            iri_to_uri('http://日本語.jp/'),
            'http://xn--wgv71a119e.jp/')
        self.assertEqual(
            iri_to_uri('http://导航.中国/'),
            'http://xn--fet810g.xn--fiqs8s/')

    def test_clean_podcast_url(self):
        self.assertEqual(clean_podcast_url('https://www.podtrac.com/pts/redirect.mp3/chtbl.com/track/5899E/traffic.megaphone.fm/HSW7835899191.mp3'), 'https://traffic.megaphone.fm/HSW7835899191.mp3')
        self.assertEqual(clean_podcast_url('https://play.podtrac.com/npr-344098539/edge1.pod.npr.org/anon.npr-podcasts/podcast/npr/waitwait/2020/10/20201003_waitwait_wwdtmpodcast201003-015621a5-f035-4eca-a9a1-7c118d90bc3c.mp3'), 'https://edge1.pod.npr.org/anon.npr-podcasts/podcast/npr/waitwait/2020/10/20201003_waitwait_wwdtmpodcast201003-015621a5-f035-4eca-a9a1-7c118d90bc3c.mp3')
        self.assertEqual(clean_podcast_url('https://pdst.fm/e/2.gum.fm/chtbl.com/track/chrt.fm/track/34D33/pscrb.fm/rss/p/traffic.megaphone.fm/ITLLC7765286967.mp3?updated=1687282661'), 'https://traffic.megaphone.fm/ITLLC7765286967.mp3?updated=1687282661')
        self.assertEqual(clean_podcast_url('https://pdst.fm/e/https://mgln.ai/e/441/www.buzzsprout.com/1121972/13019085-ep-252-the-deep-life-stack.mp3'), 'https://www.buzzsprout.com/1121972/13019085-ep-252-the-deep-life-stack.mp3')

    def test_LazyList(self):
        it = list(range(10))

        self.assertEqual(list(LazyList(it)), it)
        self.assertEqual(LazyList(it).exhaust(), it)
        self.assertEqual(LazyList(it)[5], it[5])

        self.assertEqual(LazyList(it)[5:], it[5:])
        self.assertEqual(LazyList(it)[:5], it[:5])
        self.assertEqual(LazyList(it)[::2], it[::2])
        self.assertEqual(LazyList(it)[1::2], it[1::2])
        self.assertEqual(LazyList(it)[5::-1], it[5::-1])
        self.assertEqual(LazyList(it)[6:2:-2], it[6:2:-2])
        self.assertEqual(LazyList(it)[::-1], it[::-1])

        self.assertTrue(LazyList(it))
        self.assertFalse(LazyList(range(0)))
        self.assertEqual(len(LazyList(it)), len(it))
        self.assertEqual(repr(LazyList(it)), repr(it))
        self.assertEqual(str(LazyList(it)), str(it))

        self.assertEqual(list(LazyList(it, reverse=True)), it[::-1])
        self.assertEqual(list(reversed(LazyList(it))[::-1]), it)
        self.assertEqual(list(reversed(LazyList(it))[1:3:7]), it[::-1][1:3:7])

    def test_LazyList_laziness(self):

        def test(ll, idx, val, cache):
            self.assertEqual(ll[idx], val)
            self.assertEqual(ll._cache, list(cache))

        ll = LazyList(range(10))
        test(ll, 0, 0, range(1))
        test(ll, 5, 5, range(6))
        test(ll, -3, 7, range(10))

        ll = LazyList(range(10), reverse=True)
        test(ll, -1, 0, range(1))
        test(ll, 3, 6, range(10))

        ll = LazyList(itertools.count())
        test(ll, 10, 10, range(11))
        ll = reversed(ll)
        test(ll, -15, 14, range(15))

    def test_format_bytes(self):
        self.assertEqual(format_bytes(0), '0.00B')
        self.assertEqual(format_bytes(1000), '1000.00B')
        self.assertEqual(format_bytes(1024), '1.00KiB')
        self.assertEqual(format_bytes(1024**2), '1.00MiB')
        self.assertEqual(format_bytes(1024**3), '1.00GiB')
        self.assertEqual(format_bytes(1024**4), '1.00TiB')
        self.assertEqual(format_bytes(1024**5), '1.00PiB')
        self.assertEqual(format_bytes(1024**6), '1.00EiB')
        self.assertEqual(format_bytes(1024**7), '1.00ZiB')
        self.assertEqual(format_bytes(1024**8), '1.00YiB')
        self.assertEqual(format_bytes(1024**9), '1024.00YiB')

    def test_hide_login_info(self):
        self.assertEqual(Config.hide_login_info(['-u', 'foo', '-p', 'bar']),
                         ['-u', 'PRIVATE', '-p', 'PRIVATE'])
        self.assertEqual(Config.hide_login_info(['-u']), ['-u'])
        self.assertEqual(Config.hide_login_info(['-u', 'foo', '-u', 'bar']),
                         ['-u', 'PRIVATE', '-u', 'PRIVATE'])
        self.assertEqual(Config.hide_login_info(['--username=foo']),
                         ['--username=PRIVATE'])

    def test_locked_file(self):
        TEXT = 'test_locked_file\n'
        FILE = 'test_locked_file.ytdl'
        MODES = 'war'  # Order is important

        try:
            for lock_mode in MODES:
                with locked_file(FILE, lock_mode, False) as f:
                    if lock_mode == 'r':
                        self.assertEqual(f.read(), TEXT * 2, 'Wrong file content')
                    else:
                        f.write(TEXT)
                    for test_mode in MODES:
                        testing_write = test_mode != 'r'
                        try:
                            with locked_file(FILE, test_mode, False):
                                pass
                        except (BlockingIOError, PermissionError):
                            if not testing_write:  # FIXME: blocked read access
                                print(f'Known issue: Exclusive lock ({lock_mode}) blocks read access ({test_mode})')
                                continue
                            self.assertTrue(testing_write, f'{test_mode} is blocked by {lock_mode}')
                        else:
                            self.assertFalse(testing_write, f'{test_mode} is not blocked by {lock_mode}')
        finally:
            with contextlib.suppress(OSError):
                os.remove(FILE)

    def test_determine_file_encoding(self):
        self.assertEqual(determine_file_encoding(b''), (None, 0))
        self.assertEqual(determine_file_encoding(b'--verbose -x --audio-format mkv\n'), (None, 0))

        self.assertEqual(determine_file_encoding(b'\xef\xbb\xbf'), ('utf-8', 3))
        self.assertEqual(determine_file_encoding(b'\x00\x00\xfe\xff'), ('utf-32-be', 4))
        self.assertEqual(determine_file_encoding(b'\xff\xfe'), ('utf-16-le', 2))

        self.assertEqual(determine_file_encoding(b'\xff\xfe# coding: utf-8\n--verbose'), ('utf-16-le', 2))

        self.assertEqual(determine_file_encoding(b'# coding: utf-8\n--verbose'), ('utf-8', 0))
        self.assertEqual(determine_file_encoding(b'# coding: someencodinghere-12345\n--verbose'), ('someencodinghere-12345', 0))

        self.assertEqual(determine_file_encoding(b'#coding:utf-8\n--verbose'), ('utf-8', 0))
        self.assertEqual(determine_file_encoding(b'#  coding:   utf-8   \r\n--verbose'), ('utf-8', 0))

        self.assertEqual(determine_file_encoding('# coding: utf-32-be'.encode('utf-32-be')), ('utf-32-be', 0))
        self.assertEqual(determine_file_encoding('# coding: utf-16-le'.encode('utf-16-le')), ('utf-16-le', 0))

    def test_get_compatible_ext(self):
        self.assertEqual(get_compatible_ext(
            vcodecs=[None], acodecs=[None, None], vexts=['mp4'], aexts=['m4a', 'm4a']), 'mkv')
        self.assertEqual(get_compatible_ext(
            vcodecs=[None], acodecs=[None], vexts=['flv'], aexts=['flv']), 'flv')

        self.assertEqual(get_compatible_ext(
            vcodecs=[None], acodecs=[None], vexts=['mp4'], aexts=['m4a']), 'mp4')
        self.assertEqual(get_compatible_ext(
            vcodecs=[None], acodecs=[None], vexts=['mp4'], aexts=['webm']), 'mkv')
        self.assertEqual(get_compatible_ext(
            vcodecs=[None], acodecs=[None], vexts=['webm'], aexts=['m4a']), 'mkv')
        self.assertEqual(get_compatible_ext(
            vcodecs=[None], acodecs=[None], vexts=['webm'], aexts=['webm']), 'webm')
        self.assertEqual(get_compatible_ext(
            vcodecs=[None], acodecs=[None], vexts=['webm'], aexts=['weba']), 'webm')

        self.assertEqual(get_compatible_ext(
            vcodecs=['h264'], acodecs=['mp4a'], vexts=['mov'], aexts=['m4a']), 'mp4')
        self.assertEqual(get_compatible_ext(
            vcodecs=['av01.0.12M.08'], acodecs=['opus'], vexts=['mp4'], aexts=['webm']), 'webm')

        self.assertEqual(get_compatible_ext(
            vcodecs=['vp9'], acodecs=['opus'], vexts=['webm'], aexts=['webm'], preferences=['flv', 'mp4']), 'mp4')
        self.assertEqual(get_compatible_ext(
            vcodecs=['av1'], acodecs=['mp4a'], vexts=['webm'], aexts=['m4a'], preferences=('webm', 'mkv')), 'mkv')

    def test_try_call(self):
        def total(*x, **kwargs):
            return sum(x) + sum(kwargs.values())

        self.assertEqual(try_call(None), None,
                         msg='not a fn should give None')
        self.assertEqual(try_call(lambda: 1), 1,
                         msg='int fn with no expected_type should give int')
        self.assertEqual(try_call(lambda: 1, expected_type=int), 1,
                         msg='int fn with expected_type int should give int')
        self.assertEqual(try_call(lambda: 1, expected_type=dict), None,
                         msg='int fn with wrong expected_type should give None')
        self.assertEqual(try_call(total, args=(0, 1, 0), expected_type=int), 1,
                         msg='fn should accept arglist')
        self.assertEqual(try_call(total, kwargs={'a': 0, 'b': 1, 'c': 0}, expected_type=int), 1,
                         msg='fn should accept kwargs')
        self.assertEqual(try_call(lambda: 1, expected_type=dict), None,
                         msg='int fn with no expected_type should give None')
        self.assertEqual(try_call(lambda x: {}, total, args=(42, ), expected_type=int), 42,
                         msg='expect first int result with expected_type int')

    def test_variadic(self):
        self.assertEqual(variadic(None), (None, ))
        self.assertEqual(variadic('spam'), ('spam', ))
        self.assertEqual(variadic('spam', allowed_types=dict), 'spam')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            self.assertEqual(variadic('spam', allowed_types=[dict]), 'spam')

    def test_http_header_dict(self):
        headers = HTTPHeaderDict()
        headers['ytdl-test'] = b'0'
        self.assertEqual(list(headers.items()), [('Ytdl-Test', '0')])
        headers['ytdl-test'] = 1
        self.assertEqual(list(headers.items()), [('Ytdl-Test', '1')])
        headers['Ytdl-test'] = '2'
        self.assertEqual(list(headers.items()), [('Ytdl-Test', '2')])
        self.assertTrue('ytDl-Test' in headers)
        self.assertEqual(str(headers), str(dict(headers)))
        self.assertEqual(repr(headers), str(dict(headers)))

        headers.update({'X-dlp': 'data'})
        self.assertEqual(set(headers.items()), {('Ytdl-Test', '2'), ('X-Dlp', 'data')})
        self.assertEqual(dict(headers), {'Ytdl-Test': '2', 'X-Dlp': 'data'})
        self.assertEqual(len(headers), 2)
        self.assertEqual(headers.copy(), headers)
        headers2 = HTTPHeaderDict({'X-dlp': 'data3'}, **headers, **{'X-dlp': 'data2'})
        self.assertEqual(set(headers2.items()), {('Ytdl-Test', '2'), ('X-Dlp', 'data2')})
        self.assertEqual(len(headers2), 2)
        headers2.clear()
        self.assertEqual(len(headers2), 0)

        # ensure we prefer latter headers
        headers3 = HTTPHeaderDict({'Ytdl-TeSt': 1}, {'Ytdl-test': 2})
        self.assertEqual(set(headers3.items()), {('Ytdl-Test', '2')})
        del headers3['ytdl-tesT']
        self.assertEqual(dict(headers3), {})

        headers4 = HTTPHeaderDict({'ytdl-test': 'data;'})
        self.assertEqual(set(headers4.items()), {('Ytdl-Test', 'data;')})

        # common mistake: strip whitespace from values
        # https://github.com/yt-dlp/yt-dlp/issues/8729
        headers5 = HTTPHeaderDict({'ytdl-test': ' data; '})
        self.assertEqual(set(headers5.items()), {('Ytdl-Test', 'data;')})

    def test_extract_basic_auth(self):
        assert extract_basic_auth('http://:foo.bar') == ('http://:foo.bar', None)
        assert extract_basic_auth('http://foo.bar') == ('http://foo.bar', None)
        assert extract_basic_auth('http://@foo.bar') == ('http://foo.bar', 'Basic Og==')
        assert extract_basic_auth('http://:pass@foo.bar') == ('http://foo.bar', 'Basic OnBhc3M=')
        assert extract_basic_auth('http://user:@foo.bar') == ('http://foo.bar', 'Basic dXNlcjo=')
        assert extract_basic_auth('http://user:pass@foo.bar') == ('http://foo.bar', 'Basic dXNlcjpwYXNz')

    @unittest.skipUnless(compat_os_name == 'nt', 'Only relevant on Windows')
    def test_windows_escaping(self):
        tests = [
            'test"&',
            '%CMDCMDLINE:~-1%&',
            'a\nb',
            '"',
            '\\',
            '!',
            '^!',
            'a \\ b',
            'a \\" b',
            'a \\ b\\',
            # We replace \r with \n
            ('a\r\ra', 'a\n\na'),
        ]

        def run_shell(args):
            stdout, stderr, error = Popen.run(
                args, text=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            assert not stderr
            assert not error
            return stdout

        for argument in tests:
            if isinstance(argument, str):
                expected = argument
            else:
                argument, expected = argument

            args = [sys.executable, '-c', 'import sys; print(end=sys.argv[1])', argument, 'end']
            assert run_shell(args) == expected
            assert run_shell(shell_quote(args, shell=True)) == expected


if __name__ == '__main__':
    unittest.main()
