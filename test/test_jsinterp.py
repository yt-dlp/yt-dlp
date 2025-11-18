#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math

from yt_dlp.jsinterp import JS_Undefined, JSInterpreter, js_number_to_string


class NaN:
    pass


class TestJSInterpreter(unittest.TestCase):
    def _test(self, jsi_or_code, expected, func='f', args=()):
        if isinstance(jsi_or_code, str):
            jsi_or_code = JSInterpreter(jsi_or_code)
        got = jsi_or_code.call_function(func, *args)
        if expected is NaN:
            self.assertTrue(math.isnan(got), f'{got} is not NaN')
        else:
            self.assertEqual(got, expected)

    def test_basic(self):
        jsi = JSInterpreter('function f(){;}')
        self.assertEqual(repr(jsi.extract_function('f')), 'F<f>')
        self._test(jsi, None)

        self._test('function f(){return 42;}', 42)
        self._test('function f(){42}', None)
        self._test('var f = function(){return 42;}', 42)

    def test_add(self):
        self._test('function f(){return 42 + 7;}', 49)
        self._test('function f(){return 42 + undefined;}', NaN)
        self._test('function f(){return 42 + null;}', 42)

    def test_sub(self):
        self._test('function f(){return 42 - 7;}', 35)
        self._test('function f(){return 42 - undefined;}', NaN)
        self._test('function f(){return 42 - null;}', 42)

    def test_mul(self):
        self._test('function f(){return 42 * 7;}', 294)
        self._test('function f(){return 42 * undefined;}', NaN)
        self._test('function f(){return 42 * null;}', 0)

    def test_div(self):
        jsi = JSInterpreter('function f(a, b){return a / b;}')
        self._test(jsi, NaN, args=(0, 0))
        self._test(jsi, NaN, args=(JS_Undefined, 1))
        self._test(jsi, float('inf'), args=(2, 0))
        self._test(jsi, 0, args=(0, 3))

    def test_mod(self):
        self._test('function f(){return 42 % 7;}', 0)
        self._test('function f(){return 42 % 0;}', NaN)
        self._test('function f(){return 42 % undefined;}', NaN)

    def test_exp(self):
        self._test('function f(){return 42 ** 2;}', 1764)
        self._test('function f(){return 42 ** undefined;}', NaN)
        self._test('function f(){return 42 ** null;}', 1)
        self._test('function f(){return undefined ** 42;}', NaN)

    def test_calc(self):
        self._test('function f(a){return 2*a+1;}', 7, args=[3])

    def test_empty_return(self):
        self._test('function f(){return; y()}', None)

    def test_morespace(self):
        self._test('function f (a) { return 2 * a + 1 ; }', 7, args=[3])
        self._test('function f () { x =  2  ; return x; }', 2)

    def test_strange_chars(self):
        self._test('function $_xY1 ($_axY1) { var $_axY2 = $_axY1 + 1; return $_axY2; }',
                   21, args=[20], func='$_xY1')

    def test_operators(self):
        self._test('function f(){return 1 << 5;}', 32)
        self._test('function f(){return 2 ** 5}', 32)
        self._test('function f(){return 19 & 21;}', 17)
        self._test('function f(){return 11 >> 2;}', 2)
        self._test('function f(){return []? 2+3: 4;}', 5)
        self._test('function f(){return 1 == 2}', False)
        self._test('function f(){return 0 && 1 || 2;}', 2)
        self._test('function f(){return 0 ?? 42;}', 0)
        self._test('function f(){return "life, the universe and everything" < 42;}', False)
        self._test('function f(){return 0  - 7 * - 6;}', 42)
        self._test('function f(){return true << "5";}', 32)
        self._test('function f(){return true << true;}', 2)
        self._test('function f(){return "19" & "21.9";}', 17)
        self._test('function f(){return "19" & false;}', 0)
        self._test('function f(){return "11.0" >> "2.1";}', 2)
        self._test('function f(){return 5 ^ 9;}', 12)
        self._test('function f(){return 0.0 << NaN}', 0)
        self._test('function f(){return null << undefined}', 0)
        # TODO: Does not work due to number too large
        # self._test('function f(){return 21 << 4294967297}', 42)

    def test_array_access(self):
        self._test('function f(){var x = [1,2,3]; x[0] = 4; x[0] = 5; x[2.0] = 7; return x;}', [5, 2, 7])

    def test_parens(self):
        self._test('function f(){return (1) + (2) * ((( (( (((((3)))))) )) ));}', 7)
        self._test('function f(){return (1 + 2) * 3;}', 9)

    def test_quotes(self):
        self._test(R'function f(){return "a\"\\("}', R'a"\(')

    def test_assignments(self):
        self._test('function f(){var x = 20; x = 30 + 1; return x;}', 31)
        self._test('function f(){var x = 20; x += 30 + 1; return x;}', 51)
        self._test('function f(){var x = 20; x -= 30 + 1; return x;}', -11)
        self._test('function f(){var x = 2; var y = ["a", "b"]; y[x%y["length"]]="z"; return y}', ['z', 'b'])

    @unittest.skip('Not implemented')
    def test_comments(self):
        self._test('''
            function f() {
                var x = /* 1 + */ 2;
                var y = /* 30
                * 40 */ 50;
                return x + y;
            }
        ''', 52)

        self._test('''
            function f() {
                var x = "/*";
                var y = 1 /* comment */ + 2;
                return y;
            }
        ''', 3)

    def test_precedence(self):
        self._test('''
            function f() {
                var a = [10, 20, 30, 40, 50];
                var b = 6;
                a[0]=a[b%a.length];
                return a;
            }
        ''', [20, 20, 30, 40, 50])

    def test_builtins(self):
        self._test('function f() { return NaN }', NaN)

    def test_date(self):
        self._test('function f() { return new Date("Wednesday 31 December 1969 18:01:26 MDT") - 0; }', 86000)

        jsi = JSInterpreter('function f(dt) { return new Date(dt) - 0; }')
        self._test(jsi, 86000, args=['Wednesday 31 December 1969 18:01:26 MDT'])
        self._test(jsi, 86000, args=['12/31/1969 18:01:26 MDT'])  # m/d/y
        self._test(jsi, 0, args=['1 January 1970 00:00:00 UTC'])

    def test_call(self):
        jsi = JSInterpreter('''
            function x() { return 2; }
            function y(a) { return x() + (a?a:0); }
            function z() { return y(3); }
        ''')
        self._test(jsi, 5, func='z')
        self._test(jsi, 2, func='y')

    def test_if(self):
        self._test('''
            function f() {
                let a = 9;
                if (0==0) {a++}
                return a
            }
        ''', 10)

        self._test('''
            function f() {
                if (0==0) {return 10}
            }
        ''', 10)

        self._test('''
            function f() {
                if (0!=0) {return 1}
                else {return 10}
            }
        ''', 10)

        """  # Unsupported
        self._test('''
            function f() {
                if (0!=0) {return 1}
                else if (1==0) {return 2}
                else {return 10}
            }
        ''', 10)
        """

    def test_for_loop(self):
        self._test('function f() { a=0; for (i=0; i-10; i++) {a++} return a }', 10)

    def test_switch(self):
        jsi = JSInterpreter('''
            function f(x) { switch(x){
                case 1:x+=1;
                case 2:x+=2;
                case 3:x+=3;break;
                case 4:x+=4;
                default:x=0;
            } return x }
        ''')
        self._test(jsi, 7, args=[1])
        self._test(jsi, 6, args=[3])
        self._test(jsi, 0, args=[5])

    def test_switch_default(self):
        jsi = JSInterpreter('''
            function f(x) { switch(x){
                case 2: x+=2;
                default: x-=1;
                case 5:
                case 6: x+=6;
                case 0: break;
                case 1: x+=1;
            } return x }
        ''')
        self._test(jsi, 2, args=[1])
        self._test(jsi, 11, args=[5])
        self._test(jsi, 14, args=[9])

    def test_try(self):
        self._test('function f() { try{return 10} catch(e){return 5} }', 10)

    def test_catch(self):
        self._test('function f() { try{throw 10} catch(e){return 5} }', 5)

    def test_finally(self):
        self._test('function f() { try{throw 10} finally {return 42} }', 42)
        self._test('function f() { try{throw 10} catch(e){return 5} finally {return 42} }', 42)

    def test_nested_try(self):
        self._test('''
            function f() {try {
                try{throw 10} finally {throw 42}
                } catch(e){return 5} }
        ''', 5)

    def test_for_loop_continue(self):
        self._test('function f() { a=0; for (i=0; i-10; i++) { continue; a++ } return a }', 0)

    def test_for_loop_break(self):
        self._test('function f() { a=0; for (i=0; i-10; i++) { break; a++ } return a }', 0)

    def test_for_loop_try(self):
        self._test('''
            function f() {
                for (i=0; i-10; i++) { try { if (i == 5) throw i} catch {return 10} finally {break} };
                return 42 }
        ''', 42)

    def test_literal_list(self):
        self._test('function f() { return [1, 2, "asdf", [5, 6, 7]][3] }', [5, 6, 7])

    def test_comma(self):
        self._test('function f() { a=5; a -= 1, a+=3; return a }', 7)
        self._test('function f() { a=5; return (a -= 1, a+=3, a); }', 7)
        self._test('function f() { return (l=[0,1,2,3], function(a, b){return a+b})((l[1], l[2]), l[3]) }', 5)

    def test_void(self):
        self._test('function f() { return void 42; }', None)

    def test_return_function(self):
        jsi = JSInterpreter('''
            function f() { return [1, function(){return 1}][1] }
        ''')
        self.assertEqual(jsi.call_function('f')([]), 1)

    def test_null(self):
        self._test('function f() { return null; }', None)
        self._test('function f() { return [null > 0, null < 0, null == 0, null === 0]; }',
                   [False, False, False, False])
        self._test('function f() { return [null >= 0, null <= 0]; }', [True, True])

    def test_undefined(self):
        self._test('function f() { return undefined === undefined; }', True)
        self._test('function f() { return undefined; }', JS_Undefined)
        self._test('function f() {return undefined ?? 42; }', 42)
        self._test('function f() { let v; return v; }', JS_Undefined)
        self._test('function f() { let v; return v**0; }', 1)
        self._test('function f() { let v; return [v>42, v<=42, v&&42, 42&&v]; }',
                   [False, False, JS_Undefined, JS_Undefined])

        self._test('''
            function f() { return [
                undefined === undefined,
                undefined == undefined,
                undefined == null,
                undefined < undefined,
                undefined > undefined,
                undefined === 0,
                undefined == 0,
                undefined < 0,
                undefined > 0,
                undefined >= 0,
                undefined <= 0,
                undefined > null,
                undefined < null,
                undefined === null
            ]; }
        ''', list(map(bool, (1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))))

        jsi = JSInterpreter('''
            function f() { let v; return [42+v, v+42, v**42, 42**v, 0**v]; }
        ''')
        for y in jsi.call_function('f'):
            self.assertTrue(math.isnan(y))

    def test_object(self):
        self._test('function f() { return {}; }', {})
        self._test('function f() { let a = {m1: 42, m2: 0 }; return [a["m1"], a.m2]; }', [42, 0])
        self._test('function f() { let a; return a?.qq; }', JS_Undefined)
        self._test('function f() { let a = {m1: 42, m2: 0 }; return a?.qq; }', JS_Undefined)

    def test_regex(self):
        self._test('function f() { let a=/,,[/,913,/](,)}/; }', None)
        self._test('function f() { let a=/,,[/,913,/](,)}/; return a; }', R'/,,[/,913,/](,)}/0')

        R'''  # We are not compiling regex
        jsi = JSInterpreter('function f() { let a=/,,[/,913,/](,)}/; return a; }')
        self.assertIsInstance(jsi.call_function('f'), re.Pattern)

        jsi = JSInterpreter('function f() { let a=/,,[/,913,/](,)}/i; return a; }')
        self.assertEqual(jsi.call_function('f').flags & re.I, re.I)

        jsi = JSInterpreter(R'function f() { let a=/,][}",],()}(\[)/; return a; }')
        self.assertEqual(jsi.call_function('f').pattern, r',][}",],()}(\[)')

        jsi = JSInterpreter(R'function f() { let a=[/[)\\]/]; return a[0]; }')
        self.assertEqual(jsi.call_function('f').pattern, r'[)\\]')
        '''

    @unittest.skip('Not implemented')
    def test_replace(self):
        self._test('function f() { let a="data-name".replace("data-", ""); return a }',
                   'name')
        self._test('function f() { let a="data-name".replace(new RegExp("^.+-"), ""); return a; }',
                   'name')
        self._test('function f() { let a="data-name".replace(/^.+-/, ""); return a; }',
                   'name')
        self._test('function f() { let a="data-name".replace(/a/g, "o"); return a; }',
                   'doto-nome')
        self._test('function f() { let a="data-name".replaceAll("a", "o"); return a; }',
                   'doto-nome')

    def test_char_code_at(self):
        jsi = JSInterpreter('function f(i){return "test".charCodeAt(i)}')
        self._test(jsi, 116, args=[0])
        self._test(jsi, 101, args=[1])
        self._test(jsi, 115, args=[2])
        self._test(jsi, 116, args=[3])
        self._test(jsi, None, args=[4])
        self._test(jsi, 116, args=['not_a_number'])

    def test_bitwise_operators_overflow(self):
        self._test('function f(){return -524999584 << 5}', 379882496)
        self._test('function f(){return 1236566549 << 5}', 915423904)

    def test_bitwise_operators_typecast(self):
        self._test('function f(){return null << 5}', 0)
        self._test('function f(){return undefined >> 5}', 0)
        self._test('function f(){return 42 << NaN}', 42)

    def test_negative(self):
        self._test('function f(){return 2    *    -2.0    ;}', -4)
        self._test('function f(){return 2    -    - -2    ;}', 0)
        self._test('function f(){return 2    -    - - -2  ;}', 4)
        self._test('function f(){return 2    -    + + - -2;}', 0)
        self._test('function f(){return 2    +    - + - -2;}', 0)

    @unittest.skip('Not implemented')
    def test_packed(self):
        jsi = JSInterpreter('''function f(p,a,c,k,e,d){while(c--)if(k[c])p=p.replace(new RegExp('\\b'+c.toString(a)+'\\b','g'),k[c]);return p}''')
        self.assertEqual(jsi.call_function('f', '''h 7=g("1j");7.7h({7g:[{33:"w://7f-7e-7d-7c.v.7b/7a/79/78/77/76.74?t=73&s=2s&e=72&f=2t&71=70.0.0.1&6z=6y&6x=6w"}],6v:"w://32.v.u/6u.31",16:"r%",15:"r%",6t:"6s",6r:"",6q:"l",6p:"l",6o:"6n",6m:\'6l\',6k:"6j",9:[{33:"/2u?b=6i&n=50&6h=w://32.v.u/6g.31",6f:"6e"}],1y:{6d:1,6c:\'#6b\',6a:\'#69\',68:"67",66:30,65:r,},"64":{63:"%62 2m%m%61%5z%5y%5x.u%5w%5v%5u.2y%22 2k%m%1o%22 5t%m%1o%22 5s%m%1o%22 2j%m%5r%22 16%m%5q%22 15%m%5p%22 5o%2z%5n%5m%2z",5l:"w://v.u/d/1k/5k.2y",5j:[]},\'5i\':{"5h":"5g"},5f:"5e",5d:"w://v.u",5c:{},5b:l,1x:[0.25,0.50,0.75,1,1.25,1.5,2]});h 1m,1n,5a;h 59=0,58=0;h 7=g("1j");h 2x=0,57=0,56=0;$.55({54:{\'53-52\':\'2i-51\'}});7.j(\'4z\',6(x){c(5>0&&x.1l>=5&&1n!=1){1n=1;$(\'q.4y\').4x(\'4w\')}});7.j(\'13\',6(x){2x=x.1l});7.j(\'2g\',6(x){2w(x)});7.j(\'4v\',6(){$(\'q.2v\').4u()});6 2w(x){$(\'q.2v\').4t();c(1m)19;1m=1;17=0;c(4s.4r===l){17=1}$.4q(\'/2u?b=4p&2l=1k&4o=2t-4n-4m-2s-4l&4k=&4j=&4i=&17=\'+17,6(2r){$(\'#4h\').4g(2r)});$(\'.3-8-4f-4e:4d("4c")\').2h(6(e){2q();g().4b(0);g().4a(l)});6 2q(){h $14=$("<q />").2p({1l:"49",16:"r%",15:"r%",48:0,2n:0,2o:47,46:"45(10%, 10%, 10%, 0.4)","44-43":"42"});$("<41 />").2p({16:"60%",15:"60%",2o:40,"3z-2n":"3y"}).3x({\'2m\':\'/?b=3w&2l=1k\',\'2k\':\'0\',\'2j\':\'2i\'}).2f($14);$14.2h(6(){$(3v).3u();g().2g()});$14.2f($(\'#1j\'))}g().13(0);}6 3t(){h 9=7.1b(2e);2d.2c(9);c(9.n>1){1r(i=0;i<9.n;i++){c(9[i].1a==2e){2d.2c(\'!!=\'+i);7.1p(i)}}}}7.j(\'3s\',6(){g().1h("/2a/3r.29","3q 10 28",6(){g().13(g().27()+10)},"2b");$("q[26=2b]").23().21(\'.3-20-1z\');g().1h("/2a/3p.29","3o 10 28",6(){h 12=g().27()-10;c(12<0)12=0;g().13(12)},"24");$("q[26=24]").23().21(\'.3-20-1z\');});6 1i(){}7.j(\'3n\',6(){1i()});7.j(\'3m\',6(){1i()});7.j("k",6(y){h 9=7.1b();c(9.n<2)19;$(\'.3-8-3l-3k\').3j(6(){$(\'#3-8-a-k\').1e(\'3-8-a-z\');$(\'.3-a-k\').p(\'o-1f\',\'11\')});7.1h("/3i/3h.3g","3f 3e",6(){$(\'.3-1w\').3d(\'3-8-1v\');$(\'.3-8-1y, .3-8-1x\').p(\'o-1g\',\'11\');c($(\'.3-1w\').3c(\'3-8-1v\')){$(\'.3-a-k\').p(\'o-1g\',\'l\');$(\'.3-a-k\').p(\'o-1f\',\'l\');$(\'.3-8-a\').1e(\'3-8-a-z\');$(\'.3-8-a:1u\').3b(\'3-8-a-z\')}3a{$(\'.3-a-k\').p(\'o-1g\',\'11\');$(\'.3-a-k\').p(\'o-1f\',\'11\');$(\'.3-8-a:1u\').1e(\'3-8-a-z\')}},"39");7.j("38",6(y){1d.37(\'1c\',y.9[y.36].1a)});c(1d.1t(\'1c\')){35("1s(1d.1t(\'1c\'));",34)}});h 18;6 1s(1q){h 9=7.1b();c(9.n>1){1r(i=0;i<9.n;i++){c(9[i].1a==1q){c(i==18){19}18=i;7.1p(i)}}}}',36,270,'|||jw|||function|player|settings|tracks|submenu||if||||jwplayer|var||on|audioTracks|true|3D|length|aria|attr|div|100|||sx|filemoon|https||event|active||false|tt|seek|dd|height|width|adb|current_audio|return|name|getAudioTracks|default_audio|localStorage|removeClass|expanded|checked|addButton|callMeMaybe|vplayer|0fxcyc2ajhp1|position|vvplay|vvad|220|setCurrentAudioTrack|audio_name|for|audio_set|getItem|last|open|controls|playbackRates|captions|rewind|icon|insertAfter||detach|ff00||button|getPosition|sec|png|player8|ff11|log|console|track_name|appendTo|play|click|no|scrolling|frameborder|file_code|src|top|zIndex|css|showCCform|data|1662367683|383371|dl|video_ad|doPlay|prevt|mp4|3E||jpg|thumbs|file|300|setTimeout|currentTrack|setItem|audioTrackChanged|dualSound|else|addClass|hasClass|toggleClass|Track|Audio|svg|dualy|images|mousedown|buttons|topbar|playAttemptFailed|beforePlay|Rewind|fr|Forward|ff|ready|set_audio_track|remove|this|upload_srt|prop|50px|margin|1000001|iframe|center|align|text|rgba|background|1000000|left|absolute|pause|setCurrentCaptions|Upload|contains|item|content|html|fviews|referer|prem|embed|3e57249ef633e0d03bf76ceb8d8a4b65|216|83|hash|view|get|TokenZir|window|hide|show|complete|slow|fadeIn|video_ad_fadein|time||cache|Cache|Content|headers|ajaxSetup|v2done|tott|vastdone2|vastdone1|vvbefore|playbackRateControls|cast|aboutlink|FileMoon|abouttext|UHD|1870|qualityLabels|sites|GNOME_POWER|link|2Fiframe|3C|allowfullscreen|22360|22640|22no|marginheight|marginwidth|2FGNOME_POWER|2F0fxcyc2ajhp1|2Fe|2Ffilemoon|2F|3A||22https|3Ciframe|code|sharing|fontOpacity|backgroundOpacity|Tahoma|fontFamily|303030|backgroundColor|FFFFFF|color|userFontScale|thumbnails|kind|0fxcyc2ajhp10000|url|get_slides|start|startparam|none|preload|html5|primary|hlshtml|androidhls|duration|uniform|stretching|0fxcyc2ajhp1_xt|image|2048|sp|6871|asn|127|srv|43200|_g3XlBcu2lmD9oDexD2NLWSmah2Nu3XcDrl93m9PwXY|m3u8||master|0fxcyc2ajhp1_x|00076|01|hls2|to|s01|delivery|storage|moon|sources|setup'''.split('|')))  # noqa: SIM905

    def test_join(self):
        test_input = list('test')
        tests = [
            'function f(a, b){return a.join(b)}',
            'function f(a, b){return Array.prototype.join.call(a, b)}',
            'function f(a, b){return Array.prototype.join.apply(a, [b])}',
        ]
        for test in tests:
            jsi = JSInterpreter(test)
            self._test(jsi, 'test', args=[test_input, ''])
            self._test(jsi, 't-e-s-t', args=[test_input, '-'])
            self._test(jsi, '', args=[[], '-'])

    def test_split(self):
        test_result = list('test')
        tests = [
            'function f(a, b){return a.split(b)}',
            'function f(a, b){return a["split"](b)}',
            'function f(a, b){let x = ["split"]; return a[x[0]](b)}',
            'function f(a, b){return String.prototype.split.call(a, b)}',
            'function f(a, b){return String.prototype.split.apply(a, [b])}',
        ]
        for test in tests:
            jsi = JSInterpreter(test)
            self._test(jsi, test_result, args=['test', ''])
            self._test(jsi, test_result, args=['t-e-s-t', '-'])
            self._test(jsi, [''], args=['', '-'])
            self._test(jsi, [], args=['', ''])

    def test_slice(self):
        self._test('function f(){return [0, 1, 2, 3, 4, 5, 6, 7, 8].slice()}', [0, 1, 2, 3, 4, 5, 6, 7, 8])
        self._test('function f(){return [0, 1, 2, 3, 4, 5, 6, 7, 8].slice(0)}', [0, 1, 2, 3, 4, 5, 6, 7, 8])
        self._test('function f(){return [0, 1, 2, 3, 4, 5, 6, 7, 8].slice(5)}', [5, 6, 7, 8])
        self._test('function f(){return [0, 1, 2, 3, 4, 5, 6, 7, 8].slice(99)}', [])
        self._test('function f(){return [0, 1, 2, 3, 4, 5, 6, 7, 8].slice(-2)}', [7, 8])
        self._test('function f(){return [0, 1, 2, 3, 4, 5, 6, 7, 8].slice(-99)}', [0, 1, 2, 3, 4, 5, 6, 7, 8])
        self._test('function f(){return [0, 1, 2, 3, 4, 5, 6, 7, 8].slice(0, 0)}', [])
        self._test('function f(){return [0, 1, 2, 3, 4, 5, 6, 7, 8].slice(1, 0)}', [])
        self._test('function f(){return [0, 1, 2, 3, 4, 5, 6, 7, 8].slice(0, 1)}', [0])
        self._test('function f(){return [0, 1, 2, 3, 4, 5, 6, 7, 8].slice(3, 6)}', [3, 4, 5])
        self._test('function f(){return [0, 1, 2, 3, 4, 5, 6, 7, 8].slice(1, -1)}', [1, 2, 3, 4, 5, 6, 7])
        self._test('function f(){return [0, 1, 2, 3, 4, 5, 6, 7, 8].slice(-1, 1)}', [])
        self._test('function f(){return [0, 1, 2, 3, 4, 5, 6, 7, 8].slice(-3, -1)}', [6, 7])
        self._test('function f(){return "012345678".slice()}', '012345678')
        self._test('function f(){return "012345678".slice(0)}', '012345678')
        self._test('function f(){return "012345678".slice(5)}', '5678')
        self._test('function f(){return "012345678".slice(99)}', '')
        self._test('function f(){return "012345678".slice(-2)}', '78')
        self._test('function f(){return "012345678".slice(-99)}', '012345678')
        self._test('function f(){return "012345678".slice(0, 0)}', '')
        self._test('function f(){return "012345678".slice(1, 0)}', '')
        self._test('function f(){return "012345678".slice(0, 1)}', '0')
        self._test('function f(){return "012345678".slice(3, 6)}', '345')
        self._test('function f(){return "012345678".slice(1, -1)}', '1234567')
        self._test('function f(){return "012345678".slice(-1, 1)}', '')
        self._test('function f(){return "012345678".slice(-3, -1)}', '67')

    def test_splice(self):
        self._test('function f(){var T = ["0", "1", "2"]; T["splice"](2, 1, "0")[0]; return T }', ['0', '1', '0'])

    def test_js_number_to_string(self):
        for test, radix, expected in [
            (0, None, '0'),
            (-0, None, '0'),
            (0.0, None, '0'),
            (-0.0, None, '0'),
            (math.nan, None, 'NaN'),
            (-math.nan, None, 'NaN'),
            (math.inf, None, 'Infinity'),
            (-math.inf, None, '-Infinity'),
            (10 ** 21.5, 8, '526665530627250154000000'),
            (6, 2, '110'),
            (254, 16, 'fe'),
            (-10, 2, '-1010'),
            (-0xff, 2, '-11111111'),
            (0.1 + 0.2, 16, '0.4cccccccccccd'),
            (1234.1234, 10, '1234.1234'),
            # (1000000000000000128, 10, '1000000000000000100')
        ]:
            assert js_number_to_string(test, radix) == expected

    def test_extract_function(self):
        jsi = JSInterpreter('function a(b) { return b + 1; }')
        func = jsi.extract_function('a')
        self.assertEqual(func([2]), 3)

    def test_extract_function_with_global_stack(self):
        jsi = JSInterpreter('function c(d) { return d + e + f + g; }')
        func = jsi.extract_function('c', {'e': 10}, {'f': 100, 'g': 1000})
        self.assertEqual(func([1]), 1111)

    def test_extract_object(self):
        jsi = JSInterpreter('var a={};a.xy={};var xy;var zxy={};xy={z:function(){return "abc"}};')
        self.assertTrue('z' in jsi.extract_object('xy', None))

    def test_increment_decrement(self):
        self._test('function f() { var x = 1; return ++x; }', 2)
        self._test('function f() { var x = 1; return x++; }', 1)
        self._test('function f() { var x = 1; x--; return x }', 0)
        self._test('function f() { var y; var x = 1; x++, --x, x--, x--, y="z", "abc", x++; return --x }', -1)
        self._test('function f() { var a = "test--"; return a; }', 'test--')
        self._test('function f() { var b = 1; var a = "b--"; return a; }', 'b--')

    def test_nested_function_scoping(self):
        self._test(R'''
            function f() {
                var g = function() {
                    var P = 2;
                    return P;
                };
                var P = 1;
                g();
                return P;
            }
        ''', 1)
        self._test(R'''
            function f() {
                var x = function() {
                    for (var w = 1, M = []; w < 2; w++) switch (w) {
                        case 1:
                            M.push("a");
                        case 2:
                            M.push("b");
                    }
                    return M
                };
                var w = "c";
                var M = "d";
                var y = x();
                y.push(w);
                y.push(M);
                return y;
            }
        ''', ['a', 'b', 'c', 'd'])
        self._test(R'''
            function f() {
                var P, Q;
                var z = 100;
                var g = function() {
                    var P, Q; P = 2; Q = 15;
                    z = 0;
                    return P+Q;
                };
                P = 1; Q = 10;
                var x = g(), y = 3;
                return P+Q+x+y+z;
            }
        ''', 31)

    def test_undefined_varnames(self):
        jsi = JSInterpreter('function f(){ var a; return [a, b]; }')
        self._test(jsi, [JS_Undefined, JS_Undefined])
        self.assertEqual(jsi._undefined_varnames, {'b'})


if __name__ == '__main__':
    unittest.main()
