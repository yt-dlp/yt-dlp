#!/usr/bin/env python3

from __future__ import unicode_literals

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

    def test_youtube_nsig(self):
        jsi = JSInterpreter('''
        function n(a) {
            var b=a.split(""),c=[886776427,-156178677,function(d,e){e=(e%d.length+d.length)%d.length;d.splice(e,1)},
            1784036706,-371371764,235980413,function(d,e){e=(e%d.length+d.length)%d.length;d.splice(0,1,d.splice(e,1,d[0])[0])},
            1286008293,function(d,e){e=(e%d.length+d.length)%d.length;var f=d[0];d[0]=d[e];d[e]=f},
            677181136,function(d){for(var e=d.length;e;)d.push(d.splice(--e,1)[0])},
            1219079387,b,null,565464592,1036637602,b,function(d,e){for(e=(e%d.length+d.length)%d.length;e--;)d.unshift(d.pop())},
            -258655778,263048964,1590018276,-258655778,-1464634529,503797474,b,"GOH_",null,-2033769892,-1065530794,function(d,e){e=(e%d.length+d.length)%d.length;d.splice(-e).reverse().forEach(function(f){d.unshift(f)})},
            -790428566,function(d,e){for(var f=64,h=[];++f-h.length-32;){switch(f){case 58:f-=14;case 91:case 92:case 93:continue;case 123:f=47;case 94:case 95:case 96:continue;case 46:f=95}h.push(String.fromCharCode(f))}d.forEach(function(l,m,n){this.push(n[m]=h[(h.indexOf(l)-h.indexOf(this[m])+m-32+f--)%h.length])},e.split(""))},
            -1117323690,-915049167,1068829082,-1055402792,-1930280214,-611518941,1040413011,null,1564996876,166765587,1061933925,2020843377,-1776154759,146580619,772860797,1594011608,1350972156,2020843377,1350972156,function(d){d.reverse()},
            37977673];c[13]=c;c[26]=c;c[39]=c;try{c[51](c[26]),c[35](c[26],c[48]),c[1](c[4],c[0]),c[47](c[42],c[10]),c[45](c[43]),c[26](c[16],c[46]),c[3](c[6],c[38]),c[9](c[4],c[24]),c[10](c[1],c[6]),c[10](c[4],c[37]),c[27](c[51]),c[23](c[27],c[15]),c[22](c[31],c[47]),c[44](c[41],c[32]),c[45](c[10],c[12]),c[44](c[8],c[2]),c[45](c[23],c[38]),c[44](c[8],c[28]),c[45](c[21],c[18]),c[44](c[10],c[39]),c[38](c[42],c[19]),c[38](c[14],c[33]),c[38](c[14],c[17]),c[37](c[3],c[44]),c[19](c[16],c[6]),c[13](c[33],c[45]),c[36](c[33],
            c[26]),c[14](c[33],c[29]),c[30](c[6]),c[34](c[48]),c[24](c[6],c[5]),c[3](c[19],c[27]),c[5](c[41],c[45]),c[34](c[0],c[40]),c[13](c[41],c[29]),c[4](c[41],c[17]),c[36](c[0],c[24]),c[36](c[0],c[22]),c[13](c[41],c[50]),c[6](c[28],c[33]),c[14](c[28]),c[13](c[41],c[30])}catch(d){return"enhanced_except_7ZMBkuz-_w8_"+a}return b.join("")
        }''')
        self.assertEqual(jsi.call_function('n', 'iozK6raRyrJcxIfjM'), 'z-p240okzOTM-A')


if __name__ == '__main__':
    unittest.main()
