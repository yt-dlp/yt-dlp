import textwrap
import unittest

from yt_dlp.compat import compat_HTMLParseError
from yt_dlp.parsing import (
    MatchingElementParser,
    HTMLIgnoreRanges,
    HTMLTagParser,
)

extract_attributes = MatchingElementParser.extract_attributes
get_element_by_attribute = MatchingElementParser.get_element_by_attribute
get_element_by_class = MatchingElementParser.get_element_by_class
get_element_html_by_attribute = MatchingElementParser.get_element_html_by_attribute
get_element_html_by_class = MatchingElementParser.get_element_html_by_class
get_element_text_and_html_by_tag = MatchingElementParser.get_element_text_and_html_by_tag
get_elements_by_attribute = MatchingElementParser.get_elements_by_attribute
get_elements_by_class = MatchingElementParser.get_elements_by_class
get_elements_html_by_attribute = MatchingElementParser.get_elements_html_by_attribute
get_elements_html_by_class = MatchingElementParser.get_elements_html_by_class
get_elements_text_and_html_by_attribute = MatchingElementParser.get_elements_text_and_html_by_attribute
get_elements_text_and_html_by_tag = MatchingElementParser.get_elements_text_and_html_by_tag


class TestParsing(unittest.TestCase):
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

    GET_ELEMENT_BY_CLASS_TEST_STRING = '''
        <span class="foo bar">nice</span>
        <div class="foo bar">also nice</div>
    '''

    def test_get_element_by_class(self):
        html = self.GET_ELEMENT_BY_CLASS_TEST_STRING

        self.assertEqual(get_element_by_class('foo', html), 'nice')
        self.assertEqual(get_element_by_class('no-such-class', html), None)

    def test_get_element_html_by_class(self):
        html = self.GET_ELEMENT_BY_CLASS_TEST_STRING

        self.assertEqual(get_element_html_by_class('foo', html),
                         '<span class="foo bar">nice</span>')
        self.assertEqual(get_element_by_class('no-such-class', html), None)

    GET_ELEMENT_BY_ATTRIBUTE_TEST_STRING = '''
        <div itemprop="author" itemscope>foo</div>
    '''

    def test_get_element_by_attribute(self):
        html = self.GET_ELEMENT_BY_CLASS_TEST_STRING

        self.assertEqual(get_element_by_attribute('class', 'foo bar', html), 'nice')
        self.assertEqual(get_element_by_attribute('class', 'foo', html), None)
        self.assertEqual(get_element_by_attribute('class', 'no-such-foo', html), None)
        self.assertEqual(get_element_by_attribute('class', 'foo bar', html, tag='div'), 'also nice')

        html = self.GET_ELEMENT_BY_ATTRIBUTE_TEST_STRING

        self.assertEqual(get_element_by_attribute('itemprop', 'author', html), 'foo')

    def test_get_element_html_by_attribute(self):
        html = self.GET_ELEMENT_BY_CLASS_TEST_STRING

        self.assertEqual(get_element_html_by_attribute('class', 'foo bar', html),
                         '<span class="foo bar">nice</span>')
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
            'class', 'foo', '<a class="foo">nice</a><span class="foo">not nice</span>', tag='a'),
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
        self.assertIsNone(get_element_text_and_html_by_tag('article', html))

    def test_get_elements_text_and_html_by_tag(self):
        class StrictParser(MatchingElementParser):
            STRICT = True

        test_string = '''
            <img src="a.png">
            <img src="b.png" />
            <span>ignore</span>
        '''
        items = get_elements_text_and_html_by_tag('img', test_string)
        self.assertEqual(items, [('', '<img src="a.png">'), ('', '<img src="b.png" />')])

        self.assertEqual(
            StrictParser.get_element_text_and_html_by_tag('use', '<use><img></use>'),
            ('<img>', '<use><img></use>'))

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
        self.assertEqual(
            get_element_text_and_html_by_tag('orphan', f'<orphan>{html}'), ('', '<orphan>'))
        self.assertIsNone(get_element_text_and_html_by_tag('orphan', f'{html}</orphan>'))

        # ignore case on tags
        ci_html = f'<SpAn>{html}</sPaN>'
        self.assertEqual(get_element_text_and_html_by_tag('span', ci_html), (html, ci_html))

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

        tags = parser.taglist('<div><p>', reset=True)
        self.assertEqual(tags, [Tag('div'), Tag('p')])
        self.assertEqual(tags[0].text_and_html(), ('', '<div>'))
        self.assertEqual(tags[1].text_and_html(), ('', '<p>'))

        tags = parser.taglist('<div><p></div></p>', reset=True)
        self.assertEqual(tags, [Tag('div'), Tag('p')])
        self.assertEqual(tags[0].text_and_html(), ('<p>', '<div><p></div>'))
        self.assertEqual(tags[1].text_and_html(), ('</div>', '<p></div></p>'))

        tags = parser.taglist('<div><p>/p></div>', reset=True)
        self.assertEqual(tags, [Tag('div'), Tag('p')])
        self.assertEqual(tags[0].text_and_html(), ('<p>/p>', '<div><p>/p></div>'))
        self.assertEqual(tags[1].text_and_html(), ('', '<p>'))

        tags = parser.taglist('<div><p>paragraph</p<ignored></div>', reset=True)
        self.assertEqual(tags, [Tag('div'), Tag('p')])
        self.assertEqual(tags[0].text_and_html(),
                         ('<p>paragraph</p<ignored>', '<div><p>paragraph</p<ignored></div>'))
        self.assertEqual(tags[1].text_and_html(), ('paragraph', '<p>paragraph</p<ignored>'))

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

    def test_tag_return_order(self):
        Tag = HTMLTagParser.Tag
        html = '''
        <t0>
            <t1>
                <t2>
                    <t3 /> <t4 />
                </t2>
            </t1>
            <t5>
                <t6 />
            </t5>
        </t0>
        <t7>
            <t8 />
        </t7>
        '''
        parser = HTMLTagParser()
        tags = parser.taglist(html, reset=True)
        self.assertEqual(
            str(tags), str([Tag('t0'), Tag('t1'), Tag('t2'), Tag('t3'), Tag('t4'),
                            Tag('t5'), Tag('t6'), Tag('t7'), Tag('t8')]))

        tags = parser.taglist(html, reset=True, depth_first=True)
        self.assertEqual(
            str(tags), str([Tag('t3'), Tag('t4'), Tag('t2'), Tag('t1'), Tag('t6'),
                            Tag('t5'), Tag('t0'), Tag('t8'), Tag('t7')]))

        # return tags in nested order
        tags = parser.taglist(html, reset=True, depth_first=None)
        self.assertEqual(
            str(tags), str([
                [Tag('t0'),
                 [Tag('t1'),
                  [Tag('t2'), [Tag('t3')], [Tag('t4')]]],
                 [Tag('t5'), [Tag('t6')]]],
                [Tag('t7'), [Tag('t8')]]]))

    def test_html_ignored_ranges(self):
        def mark_comments(_string, char='^', nochar='-'):
            cmts = HTMLIgnoreRanges(_string)
            return "".join(char if _idx in cmts else nochar for _idx in range(len(_string)))

        html_string = '''
        no              comments         in            this              line
        ---------------------------------------------------------------------
        <!--                 whole line represents a comment              -->
        ----^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^---
        before <!--                      comment                  -->   after
        -----------^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^-----------
        this is a leftover comment -->     <!-- a new comment without closing
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^------------^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        here   is   <!-- a comment -->   and   <!-- another comment --!>  end
        ----------------^^^^^^^^^^^----------------^^^^^^^^^^^^^^^^^---------
        <script> ignore here </script>            <SCRIPT> and here </SCRIPT>
        --------^^^^^^^^^^^^^-----------------------------^^^^^^^^^^---------
        '''

        lines = textwrap.dedent(html_string).strip().splitlines()
        for line, marker in zip(lines[0::2], lines[1::2]):
            self.assertEqual((line, mark_comments(line)), (line, marker))

        # yet we must be able to match script elements
        test_string = '''<script type="text/javascript">var foo = 'bar';</script>'''
        items = get_element_text_and_html_by_tag('script', test_string)
        self.assertEqual(items, ("var foo = 'bar';", test_string))
