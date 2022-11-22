import textwrap
import unittest

from parsing import (
    FirstMatchingElementParser,
    HTMLTagParser,
    MatchingElementParser,
)

from yt_dlp.compat import compat_HTMLParseError

get_element_by_attribute = FirstMatchingElementParser
get_element_by_class = FirstMatchingElementParser
get_element_html_by_attribute = FirstMatchingElementParser
get_element_html_by_class = FirstMatchingElementParser.get_element_html_by_class
get_element_text_and_html_by_tag = FirstMatchingElementParser.get_element_text_and_html_by_tag
get_elements_by_attribute = MatchingElementParser
get_elements_by_class = MatchingElementParser
get_elements_html_by_attribute = MatchingElementParser
get_elements_html_by_class = FirstMatchingElementParser.get_elements_html_by_class
get_elements_text_and_html_by_attribute = MatchingElementParser


class TestParsing(unittest.TestCase):
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
        <span class="foo bar">nice</span>
        <span class="foo bar">also nice</span>
    '''
    GET_ELEMENTS_BY_CLASS_RES = [
        '<span class="foo bar">nice</span>',
        '<span class="foo bar">also nice</span>'
    ]

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

        self.assertEqual(get_elements_html_by_attribute('class', 'foo bar', html),
                         self.GET_ELEMENTS_BY_CLASS_RES)
        self.assertEqual(get_elements_html_by_attribute('class', 'foo', html), [])
        self.assertEqual(get_elements_html_by_attribute('class', 'no-such-foo', html), [])

    def test_get_elements_text_and_html_by_attribute(self):
        html = self.GET_ELEMENTS_BY_CLASS_TEST_STRING

        self.assertEqual(
            get_elements_text_and_html_by_attribute('class', 'foo bar', html),
            list(zip(['nice', 'also nice'], self.GET_ELEMENTS_BY_CLASS_RES)))
        self.assertEqual(get_elements_text_and_html_by_attribute('class', 'foo', html), [])
        self.assertEqual(get_elements_text_and_html_by_attribute('class', 'no-such-foo', html), [])

        self.assertEqual(get_elements_text_and_html_by_attribute(
            'class', 'foo', '<a class="foo">nice</a><span class="foo">nice</span>', tag='a'),
            [('nice', '<a class="foo">nice</a>')])

    def test_get_element_text_and_html_by_tag(self):
        get_element_by_tag_test_string = '''
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
        html = textwrap.indent(textwrap.dedent(get_element_by_tag_test_string), ' ' * 4)
        get_element_by_tag_res_outerdiv_html = html.strip()[32:276]
        get_element_by_tag_res_outerdiv_text = get_element_by_tag_res_outerdiv_html[5:-6]
        get_element_by_tag_res_innerspan_html = html.strip()[78:119]
        get_element_by_tag_res_innerspan_text = get_element_by_tag_res_innerspan_html[6:-7]

        self.assertEqual(
            get_element_text_and_html_by_tag('div', html),
            (get_element_by_tag_res_outerdiv_text, get_element_by_tag_res_outerdiv_html))
        self.assertEqual(
            get_element_text_and_html_by_tag('span', html),
            (get_element_by_tag_res_innerspan_text, get_element_by_tag_res_innerspan_html))
        self.assertRaises(compat_HTMLParseError, get_element_text_and_html_by_tag, 'article', html)

    def test_get_element_text_and_html_by_tag_malformed(self):
        inner_text = 'inner text'
        malnested_elements = f'<malnested_a><malnested_b>{inner_text}</malnested_a></malnested_b>'
        commented_html = '<!--<div>inner comment</div>-->'
        outerdiv_html = f'<div>{malnested_elements}</div>'
        html = f'{commented_html}{outerdiv_html}'

        self.assertEqual(
            get_element_text_and_html_by_tag('div', html), (malnested_elements, outerdiv_html))
        self.assertEqual(
            get_element_text_and_html_by_tag('malnested_a', html),
            (f'<malnested_b>{inner_text}',
             f'<malnested_a><malnested_b>{inner_text}</malnested_a>'))
        self.assertEqual(
            get_element_text_and_html_by_tag('malnested_b', html),
            (f'{inner_text}</malnested_a>',
             f'<malnested_b>{inner_text}</malnested_a></malnested_b>'))
        self.assertRaises(
            compat_HTMLParseError, get_element_text_and_html_by_tag, 'orphan', f'{html}</orphan>')
        self.assertRaises(
            compat_HTMLParseError, get_element_text_and_html_by_tag, 'orphan', f'<orphan>{html}')

    def test_strict_html_parsing(self):
        class StrictTagParser(HTMLTagParser):
            STRICT = True

        parser = StrictTagParser()
        with self.assertRaisesRegex(compat_HTMLParseError, "stray closing tag 'p'"):
            parser.taglist('</p>', reset=True)
        with self.assertRaisesRegex(compat_HTMLParseError, "unclosed tag 'p', 'div'"):
            parser.taglist('<div><p>', reset=True)
        with self.assertRaisesRegex(compat_HTMLParseError, "malnested closing tag 'div', expected after '</p>'"):
            parser.taglist('<div><p></div></p>', reset=True)
        with self.assertRaisesRegex(compat_HTMLParseError, "malnested closing tag 'div', expected after '</p>'"):
            parser.taglist('<div><p>/p></div>', reset=True)
        with self.assertRaisesRegex(compat_HTMLParseError, "malformed closing tag 'p<<'"):
            parser.taglist('<div><p></p<< </div>', reset=True)
        with self.assertRaisesRegex(compat_HTMLParseError, "stray closing tag 'img'"):
            parser.taglist('<img>must be empty</img>', reset=True)

    def test_relaxed_html_parsing(self):
        Tag = HTMLTagParser.Tag
        parser = HTMLTagParser()

        self.assertEqual(parser.taglist('</p>', reset=True), [])
        self.assertEqual(parser.taglist('<div><p>', reset=True), [])

        tags = parser.taglist('<div><p></div></p>', reset=True)
        self.assertEqual(tags, [Tag('div'), Tag('p')])

        tags = parser.taglist('<div><p>/p></div>', reset=True)
        self.assertEqual(tags, [Tag('div')])

        tags = parser.taglist('<div><p>paragraph</p<ignored /></div>', reset=True)
        self.assertEqual(tags, [Tag('p'), Tag('div')])
        self.assertEqual(tags[0].text_and_html(), ('paragraph', '<p>paragraph</p'))

        tags = parser.taglist('<img width="300px">must be empty</img>', reset=True)
        self.assertEqual(tags, [Tag('img')])
        self.assertEqual(tags[0].text_and_html(), ('', '<img width="300px">'))

    def test_compliant_html_parsing(self):
        # certain elements don't need to be closed (see HTMLTagParser.VOID_TAGS)
        Tag = HTMLTagParser.Tag
        html = '''
            no error without closing tag: <img>
            self closing is ok: <img />
        '''
        parser = HTMLTagParser()
        tags = parser.taglist(html, reset=True)
        self.assertEqual(tags, [Tag('img'), Tag('img')])

        # don't get fooled by '>' in attributes
        html = '''<img greater_a='1>0' greater_b="1>0">'''
        tags = parser.taglist(html, reset=True)
        self.assertEqual(tags[0].text_and_html(), ('', html))
