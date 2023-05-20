#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
import re

from yt_dlp.jsinterp import JS_Undefined, JSInterpreter


class TestJSInterpreter(unittest.TestCase):
    def _test(self, code, ret, func='f', args=()):
        self.assertEqual(JSInterpreter(code).call_function(func, *args), ret)

    def test_basic(self):
        jsi = JSInterpreter('function f(){;}')
        self.assertEqual(repr(jsi.extract_function('f')), 'F<f>')
        self.assertEqual(jsi.call_function('f'), None)

        self._test('function f(){return 42;}', 42)
        self._test('function f(){42}', None)
        self._test('var f = function(){return 42;}', 42)

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

    def test_comments(self):
        'Skipping: Not yet fully implemented'
        return
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
        jsi = JSInterpreter('function f() { return NaN }')
        self.assertTrue(math.isnan(jsi.call_function('f')))

        self._test('function f() { return new Date("Wednesday 31 December 1969 18:01:26 MDT") - 0; }',
                   86000)
        self._test('function f(dt) { return new Date(dt) - 0; }',
                   86000, args=['Wednesday 31 December 1969 18:01:26 MDT'])

    def test_call(self):
        jsi = JSInterpreter('''
            function x() { return 2; }
            function y(a) { return x() + (a?a:0); }
            function z() { return y(3); }
        ''')
        self.assertEqual(jsi.call_function('z'), 5)
        self.assertEqual(jsi.call_function('y'), 2)

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
        self.assertEqual(jsi.call_function('f', 1), 7)
        self.assertEqual(jsi.call_function('f', 3), 6)
        self.assertEqual(jsi.call_function('f', 5), 0)

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
        self.assertEqual(jsi.call_function('f', 1), 2)
        self.assertEqual(jsi.call_function('f', 5), 11)
        self.assertEqual(jsi.call_function('f', 9), 14)

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

        jsi = JSInterpreter('function f() { let a=/,,[/,913,/](,)}/; return a; }')
        self.assertIsInstance(jsi.call_function('f'), re.Pattern)

        jsi = JSInterpreter('function f() { let a=/,,[/,913,/](,)}/i; return a; }')
        self.assertEqual(jsi.call_function('f').flags & re.I, re.I)

        jsi = JSInterpreter(R'function f() { let a=/,][}",],()}(\[)/; return a; }')
        self.assertEqual(jsi.call_function('f').pattern, r',][}",],()}(\[)')

        jsi = JSInterpreter(R'function f() { let a=[/[)\\]/]; return a[0]; }')
        self.assertEqual(jsi.call_function('f').pattern, r'[)\\]')

    def test_char_code_at(self):
        jsi = JSInterpreter('function f(i){return "test".charCodeAt(i)}')
        self.assertEqual(jsi.call_function('f', 0), 116)
        self.assertEqual(jsi.call_function('f', 1), 101)
        self.assertEqual(jsi.call_function('f', 2), 115)
        self.assertEqual(jsi.call_function('f', 3), 116)
        self.assertEqual(jsi.call_function('f', 4), None)
        self.assertEqual(jsi.call_function('f', 'not_a_number'), 116)

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


if __name__ == '__main__':
    unittest.main()
