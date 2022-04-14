#!/usr/bin/env python3
# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.jsinterp import JSInterpreter


class TestJSInterpreter(unittest.TestCase):
    def test_basic(self):
        jsi = JSInterpreter('function x(){;}')
        self.assertEqual(jsi.call_function('x'), None)

        jsi = JSInterpreter('function x3(){return 42;}')
        self.assertEqual(jsi.call_function('x3'), 42)

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

        jsi = JSInterpreter('function f(){return 19 & 21;}')
        self.assertEqual(jsi.call_function('f'), 17)

        jsi = JSInterpreter('function f(){return 11 >> 2;}')
        self.assertEqual(jsi.call_function('f'), 2)

    def test_array_access(self):
        jsi = JSInterpreter('function f(){var x = [1,2,3]; x[0] = 4; x[0] = 5; x[2] = 7; return x;}')
        self.assertEqual(jsi.call_function('f'), [5, 2, 7])

    def test_parens(self):
        jsi = JSInterpreter('function f(){return (1) + (2) * ((( (( (((((3)))))) )) ));}')
        self.assertEqual(jsi.call_function('f'), 7)

        jsi = JSInterpreter('function f(){return (1 + 2) * 3;}')
        self.assertEqual(jsi.call_function('f'), 9)

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

    def test_call(self):
        jsi = JSInterpreter('''
        function x() { return 2; }
        function y(a) { return x() + a; }
        function z() { return y(3); }
        ''')
        self.assertEqual(jsi.call_function('z'), 5)

    def test_for_loop(self):
        jsi = JSInterpreter('''
        function x() { a=0; for (i=0; i-10; i++) {a++} a }
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

    def test_for_loop_continue(self):
        jsi = JSInterpreter('''
        function x() { a=0; for (i=0; i-10; i++) { continue; a++ } a }
        ''')
        self.assertEqual(jsi.call_function('x'), 0)

    def test_for_loop_break(self):
        jsi = JSInterpreter('''
        function x() { a=0; for (i=0; i-10; i++) { break; a++ } a }
        ''')
        self.assertEqual(jsi.call_function('x'), 0)

    def test_literal_list(self):
        jsi = JSInterpreter('''
        function x() { [1, 2, "asdf", [5, 6, 7]][3] }
        ''')
        self.assertEqual(jsi.call_function('x'), [5, 6, 7])

    def test_comma(self):
        jsi = JSInterpreter('''
        function x() { a=5; a -= 1, a+=3; return a }
        ''')
        self.assertEqual(jsi.call_function('x'), 7)


if __name__ == '__main__':
    unittest.main()
