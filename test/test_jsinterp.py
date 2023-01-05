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
    def test_basic(self):
        jsi = JSInterpreter('function x(){;}')
        self.assertEqual(jsi.call_function('x'), None)

        jsi = JSInterpreter('function x3(){return 42;}')
        self.assertEqual(jsi.call_function('x3'), 42)

        jsi = JSInterpreter('function x3(){42}')
        self.assertEqual(jsi.call_function('x3'), None)

        jsi = JSInterpreter('var x5 = function(){return 42;}')
        self.assertEqual(jsi.call_function('x5'), 42)

    def test_calc(self):
        jsi = JSInterpreter('function x4(a){return 2*a+1;}')
        self.assertEqual(jsi.call_function('x4', 3), 7)

    def test_empty_return(self):
        jsi = JSInterpreter('function f(){return; y()}')
        self.assertEqual(jsi.call_function('f'), None)

    def test_morespace(self):
        jsi = JSInterpreter('function x (a) { return 2 * a + 1 ; }')
        self.assertEqual(jsi.call_function('x', 3), 7)

        jsi = JSInterpreter('function f () { x =  2  ; return x; }')
        self.assertEqual(jsi.call_function('f'), 2)

    def test_strange_chars(self):
        jsi = JSInterpreter('function $_xY1 ($_axY1) { var $_axY2 = $_axY1 + 1; return $_axY2; }')
        self.assertEqual(jsi.call_function('$_xY1', 20), 21)

    def test_operators(self):
        jsi = JSInterpreter('function f(){return 1 << 5;}')
        self.assertEqual(jsi.call_function('f'), 32)

        jsi = JSInterpreter('function f(){return 2 ** 5}')
        self.assertEqual(jsi.call_function('f'), 32)

        jsi = JSInterpreter('function f(){return 19 & 21;}')
        self.assertEqual(jsi.call_function('f'), 17)

        jsi = JSInterpreter('function f(){return 11 >> 2;}')
        self.assertEqual(jsi.call_function('f'), 2)

        jsi = JSInterpreter('function f(){return []? 2+3: 4;}')
        self.assertEqual(jsi.call_function('f'), 5)

        jsi = JSInterpreter('function f(){return 1 == 2}')
        self.assertEqual(jsi.call_function('f'), False)

        jsi = JSInterpreter('function f(){return 0 && 1 || 2;}')
        self.assertEqual(jsi.call_function('f'), 2)

        jsi = JSInterpreter('function f(){return 0 ?? 42;}')
        self.assertEqual(jsi.call_function('f'), 0)

        jsi = JSInterpreter('function f(){return "life, the universe and everything" < 42;}')
        self.assertFalse(jsi.call_function('f'))

    def test_array_access(self):
        jsi = JSInterpreter('function f(){var x = [1,2,3]; x[0] = 4; x[0] = 5; x[2.0] = 7; return x;}')
        self.assertEqual(jsi.call_function('f'), [5, 2, 7])

    def test_parens(self):
        jsi = JSInterpreter('function f(){return (1) + (2) * ((( (( (((((3)))))) )) ));}')
        self.assertEqual(jsi.call_function('f'), 7)

        jsi = JSInterpreter('function f(){return (1 + 2) * 3;}')
        self.assertEqual(jsi.call_function('f'), 9)

    def test_quotes(self):
        jsi = JSInterpreter(R'function f(){return "a\"\\("}')
        self.assertEqual(jsi.call_function('f'), R'a"\(')

    def test_assignments(self):
        jsi = JSInterpreter('function f(){var x = 20; x = 30 + 1; return x;}')
        self.assertEqual(jsi.call_function('f'), 31)

        jsi = JSInterpreter('function f(){var x = 20; x += 30 + 1; return x;}')
        self.assertEqual(jsi.call_function('f'), 51)

        jsi = JSInterpreter('function f(){var x = 20; x -= 30 + 1; return x;}')
        self.assertEqual(jsi.call_function('f'), -11)

    def test_comments(self):
        'Skipping: Not yet fully implemented'
        return
        jsi = JSInterpreter('''
        function x() {
            var x = /* 1 + */ 2;
            var y = /* 30
            * 40 */ 50;
            return x + y;
        }
        ''')
        self.assertEqual(jsi.call_function('x'), 52)

        jsi = JSInterpreter('''
        function f() {
            var x = "/*";
            var y = 1 /* comment */ + 2;
            return y;
        }
        ''')
        self.assertEqual(jsi.call_function('f'), 3)

    def test_precedence(self):
        jsi = JSInterpreter('''
        function x() {
            var a = [10, 20, 30, 40, 50];
            var b = 6;
            a[0]=a[b%a.length];
            return a;
        }''')
        self.assertEqual(jsi.call_function('x'), [20, 20, 30, 40, 50])

    def test_builtins(self):
        jsi = JSInterpreter('''
        function x() { return NaN }
        ''')
        self.assertTrue(math.isnan(jsi.call_function('x')))

        jsi = JSInterpreter('''
        function x() { return new Date('Wednesday 31 December 1969 18:01:26 MDT') - 0; }
        ''')
        self.assertEqual(jsi.call_function('x'), 86000)
        jsi = JSInterpreter('''
        function x(dt) { return new Date(dt) - 0; }
        ''')
        self.assertEqual(jsi.call_function('x', 'Wednesday 31 December 1969 18:01:26 MDT'), 86000)

    def test_call(self):
        jsi = JSInterpreter('''
        function x() { return 2; }
        function y(a) { return x() + (a?a:0); }
        function z() { return y(3); }
        ''')
        self.assertEqual(jsi.call_function('z'), 5)
        self.assertEqual(jsi.call_function('y'), 2)

    def test_for_loop(self):
        jsi = JSInterpreter('''
        function x() { a=0; for (i=0; i-10; i++) {a++} return a }
        ''')
        self.assertEqual(jsi.call_function('x'), 10)

    def test_switch(self):
        jsi = JSInterpreter('''
        function x(f) { switch(f){
            case 1:f+=1;
            case 2:f+=2;
            case 3:f+=3;break;
            case 4:f+=4;
            default:f=0;
        } return f }
        ''')
        self.assertEqual(jsi.call_function('x', 1), 7)
        self.assertEqual(jsi.call_function('x', 3), 6)
        self.assertEqual(jsi.call_function('x', 5), 0)

    def test_switch_default(self):
        jsi = JSInterpreter('''
        function x(f) { switch(f){
            case 2: f+=2;
            default: f-=1;
            case 5:
            case 6: f+=6;
            case 0: break;
            case 1: f+=1;
        } return f }
        ''')
        self.assertEqual(jsi.call_function('x', 1), 2)
        self.assertEqual(jsi.call_function('x', 5), 11)
        self.assertEqual(jsi.call_function('x', 9), 14)

    def test_try(self):
        jsi = JSInterpreter('''
        function x() { try{return 10} catch(e){return 5} }
        ''')
        self.assertEqual(jsi.call_function('x'), 10)

    def test_catch(self):
        jsi = JSInterpreter('''
        function x() { try{throw 10} catch(e){return 5} }
        ''')
        self.assertEqual(jsi.call_function('x'), 5)

    def test_finally(self):
        jsi = JSInterpreter('''
        function x() { try{throw 10} finally {return 42} }
        ''')
        self.assertEqual(jsi.call_function('x'), 42)
        jsi = JSInterpreter('''
        function x() { try{throw 10} catch(e){return 5} finally {return 42} }
        ''')
        self.assertEqual(jsi.call_function('x'), 42)

    def test_nested_try(self):
        jsi = JSInterpreter('''
        function x() {try {
            try{throw 10} finally {throw 42}
            } catch(e){return 5} }
        ''')
        self.assertEqual(jsi.call_function('x'), 5)

    def test_for_loop_continue(self):
        jsi = JSInterpreter('''
        function x() { a=0; for (i=0; i-10; i++) { continue; a++ } return a }
        ''')
        self.assertEqual(jsi.call_function('x'), 0)

    def test_for_loop_break(self):
        jsi = JSInterpreter('''
        function x() { a=0; for (i=0; i-10; i++) { break; a++ } return a }
        ''')
        self.assertEqual(jsi.call_function('x'), 0)

    def test_for_loop_try(self):
        jsi = JSInterpreter('''
        function x() {
            for (i=0; i-10; i++) { try { if (i == 5) throw i} catch {return 10} finally {break} };
            return 42 }
        ''')
        self.assertEqual(jsi.call_function('x'), 42)

    def test_literal_list(self):
        jsi = JSInterpreter('''
        function x() { return [1, 2, "asdf", [5, 6, 7]][3] }
        ''')
        self.assertEqual(jsi.call_function('x'), [5, 6, 7])

    def test_comma(self):
        jsi = JSInterpreter('''
        function x() { a=5; a -= 1, a+=3; return a }
        ''')
        self.assertEqual(jsi.call_function('x'), 7)

        jsi = JSInterpreter('''
        function x() { a=5; return (a -= 1, a+=3, a); }
        ''')
        self.assertEqual(jsi.call_function('x'), 7)

        jsi = JSInterpreter('''
        function x() { return (l=[0,1,2,3], function(a, b){return a+b})((l[1], l[2]), l[3]) }
        ''')
        self.assertEqual(jsi.call_function('x'), 5)

    def test_void(self):
        jsi = JSInterpreter('''
        function x() { return void 42; }
        ''')
        self.assertEqual(jsi.call_function('x'), None)

    def test_return_function(self):
        jsi = JSInterpreter('''
        function x() { return [1, function(){return 1}][1] }
        ''')
        self.assertEqual(jsi.call_function('x')([]), 1)

    def test_null(self):
        jsi = JSInterpreter('''
        function x() { return null; }
        ''')
        self.assertEqual(jsi.call_function('x'), None)

        jsi = JSInterpreter('''
        function x() { return [null > 0, null < 0, null == 0, null === 0]; }
        ''')
        self.assertEqual(jsi.call_function('x'), [False, False, False, False])

        jsi = JSInterpreter('''
        function x() { return [null >= 0, null <= 0]; }
        ''')
        self.assertEqual(jsi.call_function('x'), [True, True])

    def test_undefined(self):
        jsi = JSInterpreter('''
        function x() { return undefined === undefined; }
        ''')
        self.assertEqual(jsi.call_function('x'), True)

        jsi = JSInterpreter('''
        function x() { return undefined; }
        ''')
        self.assertEqual(jsi.call_function('x'), JS_Undefined)

        jsi = JSInterpreter('''
        function x() { let v; return v; }
        ''')
        self.assertEqual(jsi.call_function('x'), JS_Undefined)

        jsi = JSInterpreter('''
        function x() { return [undefined === undefined, undefined == undefined, undefined < undefined, undefined > undefined]; }
        ''')
        self.assertEqual(jsi.call_function('x'), [True, True, False, False])

        jsi = JSInterpreter('''
        function x() { return [undefined === 0, undefined == 0, undefined < 0, undefined > 0]; }
        ''')
        self.assertEqual(jsi.call_function('x'), [False, False, False, False])

        jsi = JSInterpreter('''
        function x() { return [undefined >= 0, undefined <= 0]; }
        ''')
        self.assertEqual(jsi.call_function('x'), [False, False])

        jsi = JSInterpreter('''
        function x() { return [undefined > null, undefined < null, undefined == null, undefined === null]; }
        ''')
        self.assertEqual(jsi.call_function('x'), [False, False, True, False])

        jsi = JSInterpreter('''
        function x() { return [undefined === null, undefined == null, undefined < null, undefined > null]; }
        ''')
        self.assertEqual(jsi.call_function('x'), [False, True, False, False])

        jsi = JSInterpreter('''
        function x() { let v; return [42+v, v+42, v**42, 42**v, 0**v]; }
        ''')
        for y in jsi.call_function('x'):
            self.assertTrue(math.isnan(y))

        jsi = JSInterpreter('''
        function x() { let v; return v**0; }
        ''')
        self.assertEqual(jsi.call_function('x'), 1)

        jsi = JSInterpreter('''
        function x() { let v; return [v>42, v<=42, v&&42, 42&&v]; }
        ''')
        self.assertEqual(jsi.call_function('x'), [False, False, JS_Undefined, JS_Undefined])

        jsi = JSInterpreter('function x(){return undefined ?? 42; }')
        self.assertEqual(jsi.call_function('x'), 42)

    def test_object(self):
        jsi = JSInterpreter('''
        function x() { return {}; }
        ''')
        self.assertEqual(jsi.call_function('x'), {})

        jsi = JSInterpreter('''
        function x() { let a = {m1: 42, m2: 0 }; return [a["m1"], a.m2]; }
        ''')
        self.assertEqual(jsi.call_function('x'), [42, 0])

        jsi = JSInterpreter('''
        function x() { let a; return a?.qq; }
        ''')
        self.assertEqual(jsi.call_function('x'), JS_Undefined)

        jsi = JSInterpreter('''
        function x() { let a = {m1: 42, m2: 0 }; return a?.qq; }
        ''')
        self.assertEqual(jsi.call_function('x'), JS_Undefined)

    def test_regex(self):
        jsi = JSInterpreter('''
        function x() { let a=/,,[/,913,/](,)}/; }
        ''')
        self.assertEqual(jsi.call_function('x'), None)

        jsi = JSInterpreter('''
        function x() { let a=/,,[/,913,/](,)}/; return a; }
        ''')
        self.assertIsInstance(jsi.call_function('x'), re.Pattern)

        jsi = JSInterpreter('''
        function x() { let a=/,,[/,913,/](,)}/i; return a; }
        ''')
        self.assertEqual(jsi.call_function('x').flags & re.I, re.I)

        jsi = JSInterpreter(R'''
        function x() { let a=/,][}",],()}(\[)/; return a; }
        ''')
        self.assertEqual(jsi.call_function('x').pattern, r',][}",],()}(\[)')

        jsi = JSInterpreter(R'''
        function x() { let a=[/[)\\]/]; return a[0]; }
        ''')
        self.assertEqual(jsi.call_function('x').pattern, r'[)\\]')

    def test_char_code_at(self):
        jsi = JSInterpreter('function x(i){return "test".charCodeAt(i)}')
        self.assertEqual(jsi.call_function('x', 0), 116)
        self.assertEqual(jsi.call_function('x', 1), 101)
        self.assertEqual(jsi.call_function('x', 2), 115)
        self.assertEqual(jsi.call_function('x', 3), 116)
        self.assertEqual(jsi.call_function('x', 4), None)
        self.assertEqual(jsi.call_function('x', 'not_a_number'), 116)

    def test_bitwise_operators_overflow(self):
        jsi = JSInterpreter('function x(){return -524999584 << 5}')
        self.assertEqual(jsi.call_function('x'), 379882496)

        jsi = JSInterpreter('function x(){return 1236566549 << 5}')
        self.assertEqual(jsi.call_function('x'), 915423904)


if __name__ == '__main__':
    unittest.main()
