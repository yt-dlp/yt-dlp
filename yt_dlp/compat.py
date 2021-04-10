# coding: utf-8
from __future__ import unicode_literals

import base64
import binascii
import collections
import ctypes
import email
import getpass
import io
import itertools
import optparse
import os
import platform
import re
import shlex
import shutil
import socket
import struct
import subprocess
import sys
import xml.etree.ElementTree


try:
    import urllib.request as compat_urllib_request
except ImportError:  # Python 2
    import urllib2 as compat_urllib_request

try:
    import urllib.error as compat_urllib_error
except ImportError:  # Python 2
    import urllib2 as compat_urllib_error

try:
    import urllib.parse as compat_urllib_parse
except ImportError:  # Python 2
    import urllib as compat_urllib_parse

try:
    import urllib.parse as compat_urlparse
except ImportError:  # Python 2
    import urlparse as compat_urlparse

try:
    from urllib.parse import urlparse as compat_urllib_parse_urlparse
except ImportError:  # Python 2
    from urlparse import urlparse as compat_urllib_parse_urlparse

try:
    from urllib.parse import urlunparse as compat_urllib_parse_urlunparse
except ImportError:  # Python 2
    from urlparse import urlunparse as compat_urllib_parse_urlunparse

try:
    import urllib.response as compat_urllib_response
except ImportError:  # Python 2
    import urllib as compat_urllib_response

try:
    import http.cookiejar as compat_cookiejar
except ImportError:  # Python 2
    import cookielib as compat_cookiejar

if sys.version_info[0] == 2:
    class compat_cookiejar_Cookie(compat_cookiejar.Cookie):
        def __init__(self, version, name, value, *args, **kwargs):
            if isinstance(name, compat_str):
                name = name.encode()
            if isinstance(value, compat_str):
                value = value.encode()
            compat_cookiejar.Cookie.__init__(self, version, name, value, *args, **kwargs)
else:
    compat_cookiejar_Cookie = compat_cookiejar.Cookie

try:
    import http.cookies as compat_cookies
except ImportError:  # Python 2
    import Cookie as compat_cookies

if sys.version_info[0] == 2:
    class compat_cookies_SimpleCookie(compat_cookies.SimpleCookie):
        def load(self, rawdata):
            if isinstance(rawdata, compat_str):
                rawdata = str(rawdata)
            return super(compat_cookies_SimpleCookie, self).load(rawdata)
else:
    compat_cookies_SimpleCookie = compat_cookies.SimpleCookie

try:
    import html.entities as compat_html_entities
except ImportError:  # Python 2
    import htmlentitydefs as compat_html_entities

try:  # Python >= 3.3
    compat_html_entities_html5 = compat_html_entities.html5
except AttributeError:
    # Copied from CPython 3.5.1 html/entities.py
    compat_html_entities_html5 = {
        'Aacute': '\xc1',
        'aacute': '\xe1',
        'Aacute;': '\xc1',
        'aacute;': '\xe1',
        'Abreve;': '\u0102',
        'abreve;': '\u0103',
        'ac;': '\u223e',
        'acd;': '\u223f',
        'acE;': '\u223e\u0333',
        'Acirc': '\xc2',
        'acirc': '\xe2',
        'Acirc;': '\xc2',
        'acirc;': '\xe2',
        'acute': '\xb4',
        'acute;': '\xb4',
        'Acy;': '\u0410',
        'acy;': '\u0430',
        'AElig': '\xc6',
        'aelig': '\xe6',
        'AElig;': '\xc6',
        'aelig;': '\xe6',
        'af;': '\u2061',
        'Afr;': '\U0001d504',
        'afr;': '\U0001d51e',
        'Agrave': '\xc0',
        'agrave': '\xe0',
        'Agrave;': '\xc0',
        'agrave;': '\xe0',
        'alefsym;': '\u2135',
        'aleph;': '\u2135',
        'Alpha;': '\u0391',
        'alpha;': '\u03b1',
        'Amacr;': '\u0100',
        'amacr;': '\u0101',
        'amalg;': '\u2a3f',
        'AMP': '&',
        'amp': '&',
        'AMP;': '&',
        'amp;': '&',
        'And;': '\u2a53',
        'and;': '\u2227',
        'andand;': '\u2a55',
        'andd;': '\u2a5c',
        'andslope;': '\u2a58',
        'andv;': '\u2a5a',
        'ang;': '\u2220',
        'ange;': '\u29a4',
        'angle;': '\u2220',
        'angmsd;': '\u2221',
        'angmsdaa;': '\u29a8',
        'angmsdab;': '\u29a9',
        'angmsdac;': '\u29aa',
        'angmsdad;': '\u29ab',
        'angmsdae;': '\u29ac',
        'angmsdaf;': '\u29ad',
        'angmsdag;': '\u29ae',
        'angmsdah;': '\u29af',
        'angrt;': '\u221f',
        'angrtvb;': '\u22be',
        'angrtvbd;': '\u299d',
        'angsph;': '\u2222',
        'angst;': '\xc5',
        'angzarr;': '\u237c',
        'Aogon;': '\u0104',
        'aogon;': '\u0105',
        'Aopf;': '\U0001d538',
        'aopf;': '\U0001d552',
        'ap;': '\u2248',
        'apacir;': '\u2a6f',
        'apE;': '\u2a70',
        'ape;': '\u224a',
        'apid;': '\u224b',
        'apos;': "'",
        'ApplyFunction;': '\u2061',
        'approx;': '\u2248',
        'approxeq;': '\u224a',
        'Aring': '\xc5',
        'aring': '\xe5',
        'Aring;': '\xc5',
        'aring;': '\xe5',
        'Ascr;': '\U0001d49c',
        'ascr;': '\U0001d4b6',
        'Assign;': '\u2254',
        'ast;': '*',
        'asymp;': '\u2248',
        'asympeq;': '\u224d',
        'Atilde': '\xc3',
        'atilde': '\xe3',
        'Atilde;': '\xc3',
        'atilde;': '\xe3',
        'Auml': '\xc4',
        'auml': '\xe4',
        'Auml;': '\xc4',
        'auml;': '\xe4',
        'awconint;': '\u2233',
        'awint;': '\u2a11',
        'backcong;': '\u224c',
        'backepsilon;': '\u03f6',
        'backprime;': '\u2035',
        'backsim;': '\u223d',
        'backsimeq;': '\u22cd',
        'Backslash;': '\u2216',
        'Barv;': '\u2ae7',
        'barvee;': '\u22bd',
        'Barwed;': '\u2306',
        'barwed;': '\u2305',
        'barwedge;': '\u2305',
        'bbrk;': '\u23b5',
        'bbrktbrk;': '\u23b6',
        'bcong;': '\u224c',
        'Bcy;': '\u0411',
        'bcy;': '\u0431',
        'bdquo;': '\u201e',
        'becaus;': '\u2235',
        'Because;': '\u2235',
        'because;': '\u2235',
        'bemptyv;': '\u29b0',
        'bepsi;': '\u03f6',
        'bernou;': '\u212c',
        'Bernoullis;': '\u212c',
        'Beta;': '\u0392',
        'beta;': '\u03b2',
        'beth;': '\u2136',
        'between;': '\u226c',
        'Bfr;': '\U0001d505',
        'bfr;': '\U0001d51f',
        'bigcap;': '\u22c2',
        'bigcirc;': '\u25ef',
        'bigcup;': '\u22c3',
        'bigodot;': '\u2a00',
        'bigoplus;': '\u2a01',
        'bigotimes;': '\u2a02',
        'bigsqcup;': '\u2a06',
        'bigstar;': '\u2605',
        'bigtriangledown;': '\u25bd',
        'bigtriangleup;': '\u25b3',
        'biguplus;': '\u2a04',
        'bigvee;': '\u22c1',
        'bigwedge;': '\u22c0',
        'bkarow;': '\u290d',
        'blacklozenge;': '\u29eb',
        'blacksquare;': '\u25aa',
        'blacktriangle;': '\u25b4',
        'blacktriangledown;': '\u25be',
        'blacktriangleleft;': '\u25c2',
        'blacktriangleright;': '\u25b8',
        'blank;': '\u2423',
        'blk12;': '\u2592',
        'blk14;': '\u2591',
        'blk34;': '\u2593',
        'block;': '\u2588',
        'bne;': '=\u20e5',
        'bnequiv;': '\u2261\u20e5',
        'bNot;': '\u2aed',
        'bnot;': '\u2310',
        'Bopf;': '\U0001d539',
        'bopf;': '\U0001d553',
        'bot;': '\u22a5',
        'bottom;': '\u22a5',
        'bowtie;': '\u22c8',
        'boxbox;': '\u29c9',
        'boxDL;': '\u2557',
        'boxDl;': '\u2556',
        'boxdL;': '\u2555',
        'boxdl;': '\u2510',
        'boxDR;': '\u2554',
        'boxDr;': '\u2553',
        'boxdR;': '\u2552',
        'boxdr;': '\u250c',
        'boxH;': '\u2550',
        'boxh;': '\u2500',
        'boxHD;': '\u2566',
        'boxHd;': '\u2564',
        'boxhD;': '\u2565',
        'boxhd;': '\u252c',
        'boxHU;': '\u2569',
        'boxHu;': '\u2567',
        'boxhU;': '\u2568',
        'boxhu;': '\u2534',
        'boxminus;': '\u229f',
        'boxplus;': '\u229e',
        'boxtimes;': '\u22a0',
        'boxUL;': '\u255d',
        'boxUl;': '\u255c',
        'boxuL;': '\u255b',
        'boxul;': '\u2518',
        'boxUR;': '\u255a',
        'boxUr;': '\u2559',
        'boxuR;': '\u2558',
        'boxur;': '\u2514',
        'boxV;': '\u2551',
        'boxv;': '\u2502',
        'boxVH;': '\u256c',
        'boxVh;': '\u256b',
        'boxvH;': '\u256a',
        'boxvh;': '\u253c',
        'boxVL;': '\u2563',
        'boxVl;': '\u2562',
        'boxvL;': '\u2561',
        'boxvl;': '\u2524',
        'boxVR;': '\u2560',
        'boxVr;': '\u255f',
        'boxvR;': '\u255e',
        'boxvr;': '\u251c',
        'bprime;': '\u2035',
        'Breve;': '\u02d8',
        'breve;': '\u02d8',
        'brvbar': '\xa6',
        'brvbar;': '\xa6',
        'Bscr;': '\u212c',
        'bscr;': '\U0001d4b7',
        'bsemi;': '\u204f',
        'bsim;': '\u223d',
        'bsime;': '\u22cd',
        'bsol;': '\\',
        'bsolb;': '\u29c5',
        'bsolhsub;': '\u27c8',
        'bull;': '\u2022',
        'bullet;': '\u2022',
        'bump;': '\u224e',
        'bumpE;': '\u2aae',
        'bumpe;': '\u224f',
        'Bumpeq;': '\u224e',
        'bumpeq;': '\u224f',
        'Cacute;': '\u0106',
        'cacute;': '\u0107',
        'Cap;': '\u22d2',
        'cap;': '\u2229',
        'capand;': '\u2a44',
        'capbrcup;': '\u2a49',
        'capcap;': '\u2a4b',
        'capcup;': '\u2a47',
        'capdot;': '\u2a40',
        'CapitalDifferentialD;': '\u2145',
        'caps;': '\u2229\ufe00',
        'caret;': '\u2041',
        'caron;': '\u02c7',
        'Cayleys;': '\u212d',
        'ccaps;': '\u2a4d',
        'Ccaron;': '\u010c',
        'ccaron;': '\u010d',
        'Ccedil': '\xc7',
        'ccedil': '\xe7',
        'Ccedil;': '\xc7',
        'ccedil;': '\xe7',
        'Ccirc;': '\u0108',
        'ccirc;': '\u0109',
        'Cconint;': '\u2230',
        'ccups;': '\u2a4c',
        'ccupssm;': '\u2a50',
        'Cdot;': '\u010a',
        'cdot;': '\u010b',
        'cedil': '\xb8',
        'cedil;': '\xb8',
        'Cedilla;': '\xb8',
        'cemptyv;': '\u29b2',
        'cent': '\xa2',
        'cent;': '\xa2',
        'CenterDot;': '\xb7',
        'centerdot;': '\xb7',
        'Cfr;': '\u212d',
        'cfr;': '\U0001d520',
        'CHcy;': '\u0427',
        'chcy;': '\u0447',
        'check;': '\u2713',
        'checkmark;': '\u2713',
        'Chi;': '\u03a7',
        'chi;': '\u03c7',
        'cir;': '\u25cb',
        'circ;': '\u02c6',
        'circeq;': '\u2257',
        'circlearrowleft;': '\u21ba',
        'circlearrowright;': '\u21bb',
        'circledast;': '\u229b',
        'circledcirc;': '\u229a',
        'circleddash;': '\u229d',
        'CircleDot;': '\u2299',
        'circledR;': '\xae',
        'circledS;': '\u24c8',
        'CircleMinus;': '\u2296',
        'CirclePlus;': '\u2295',
        'CircleTimes;': '\u2297',
        'cirE;': '\u29c3',
        'cire;': '\u2257',
        'cirfnint;': '\u2a10',
        'cirmid;': '\u2aef',
        'cirscir;': '\u29c2',
        'ClockwiseContourIntegral;': '\u2232',
        'CloseCurlyDoubleQuote;': '\u201d',
        'CloseCurlyQuote;': '\u2019',
        'clubs;': '\u2663',
        'clubsuit;': '\u2663',
        'Colon;': '\u2237',
        'colon;': ':',
        'Colone;': '\u2a74',
        'colone;': '\u2254',
        'coloneq;': '\u2254',
        'comma;': ',',
        'commat;': '@',
        'comp;': '\u2201',
        'compfn;': '\u2218',
        'complement;': '\u2201',
        'complexes;': '\u2102',
        'cong;': '\u2245',
        'congdot;': '\u2a6d',
        'Congruent;': '\u2261',
        'Conint;': '\u222f',
        'conint;': '\u222e',
        'ContourIntegral;': '\u222e',
        'Copf;': '\u2102',
        'copf;': '\U0001d554',
        'coprod;': '\u2210',
        'Coproduct;': '\u2210',
        'COPY': '\xa9',
        'copy': '\xa9',
        'COPY;': '\xa9',
        'copy;': '\xa9',
        'copysr;': '\u2117',
        'CounterClockwiseContourIntegral;': '\u2233',
        'crarr;': '\u21b5',
        'Cross;': '\u2a2f',
        'cross;': '\u2717',
        'Cscr;': '\U0001d49e',
        'cscr;': '\U0001d4b8',
        'csub;': '\u2acf',
        'csube;': '\u2ad1',
        'csup;': '\u2ad0',
        'csupe;': '\u2ad2',
        'ctdot;': '\u22ef',
        'cudarrl;': '\u2938',
        'cudarrr;': '\u2935',
        'cuepr;': '\u22de',
        'cuesc;': '\u22df',
        'cularr;': '\u21b6',
        'cularrp;': '\u293d',
        'Cup;': '\u22d3',
        'cup;': '\u222a',
        'cupbrcap;': '\u2a48',
        'CupCap;': '\u224d',
        'cupcap;': '\u2a46',
        'cupcup;': '\u2a4a',
        'cupdot;': '\u228d',
        'cupor;': '\u2a45',
        'cups;': '\u222a\ufe00',
        'curarr;': '\u21b7',
        'curarrm;': '\u293c',
        'curlyeqprec;': '\u22de',
        'curlyeqsucc;': '\u22df',
        'curlyvee;': '\u22ce',
        'curlywedge;': '\u22cf',
        'curren': '\xa4',
        'curren;': '\xa4',
        'curvearrowleft;': '\u21b6',
        'curvearrowright;': '\u21b7',
        'cuvee;': '\u22ce',
        'cuwed;': '\u22cf',
        'cwconint;': '\u2232',
        'cwint;': '\u2231',
        'cylcty;': '\u232d',
        'Dagger;': '\u2021',
        'dagger;': '\u2020',
        'daleth;': '\u2138',
        'Darr;': '\u21a1',
        'dArr;': '\u21d3',
        'darr;': '\u2193',
        'dash;': '\u2010',
        'Dashv;': '\u2ae4',
        'dashv;': '\u22a3',
        'dbkarow;': '\u290f',
        'dblac;': '\u02dd',
        'Dcaron;': '\u010e',
        'dcaron;': '\u010f',
        'Dcy;': '\u0414',
        'dcy;': '\u0434',
        'DD;': '\u2145',
        'dd;': '\u2146',
        'ddagger;': '\u2021',
        'ddarr;': '\u21ca',
        'DDotrahd;': '\u2911',
        'ddotseq;': '\u2a77',
        'deg': '\xb0',
        'deg;': '\xb0',
        'Del;': '\u2207',
        'Delta;': '\u0394',
        'delta;': '\u03b4',
        'demptyv;': '\u29b1',
        'dfisht;': '\u297f',
        'Dfr;': '\U0001d507',
        'dfr;': '\U0001d521',
        'dHar;': '\u2965',
        'dharl;': '\u21c3',
        'dharr;': '\u21c2',
        'DiacriticalAcute;': '\xb4',
        'DiacriticalDot;': '\u02d9',
        'DiacriticalDoubleAcute;': '\u02dd',
        'DiacriticalGrave;': '`',
        'DiacriticalTilde;': '\u02dc',
        'diam;': '\u22c4',
        'Diamond;': '\u22c4',
        'diamond;': '\u22c4',
        'diamondsuit;': '\u2666',
        'diams;': '\u2666',
        'die;': '\xa8',
        'DifferentialD;': '\u2146',
        'digamma;': '\u03dd',
        'disin;': '\u22f2',
        'div;': '\xf7',
        'divide': '\xf7',
        'divide;': '\xf7',
        'divideontimes;': '\u22c7',
        'divonx;': '\u22c7',
        'DJcy;': '\u0402',
        'djcy;': '\u0452',
        'dlcorn;': '\u231e',
        'dlcrop;': '\u230d',
        'dollar;': '$',
        'Dopf;': '\U0001d53b',
        'dopf;': '\U0001d555',
        'Dot;': '\xa8',
        'dot;': '\u02d9',
        'DotDot;': '\u20dc',
        'doteq;': '\u2250',
        'doteqdot;': '\u2251',
        'DotEqual;': '\u2250',
        'dotminus;': '\u2238',
        'dotplus;': '\u2214',
        'dotsquare;': '\u22a1',
        'doublebarwedge;': '\u2306',
        'DoubleContourIntegral;': '\u222f',
        'DoubleDot;': '\xa8',
        'DoubleDownArrow;': '\u21d3',
        'DoubleLeftArrow;': '\u21d0',
        'DoubleLeftRightArrow;': '\u21d4',
        'DoubleLeftTee;': '\u2ae4',
        'DoubleLongLeftArrow;': '\u27f8',
        'DoubleLongLeftRightArrow;': '\u27fa',
        'DoubleLongRightArrow;': '\u27f9',
        'DoubleRightArrow;': '\u21d2',
        'DoubleRightTee;': '\u22a8',
        'DoubleUpArrow;': '\u21d1',
        'DoubleUpDownArrow;': '\u21d5',
        'DoubleVerticalBar;': '\u2225',
        'DownArrow;': '\u2193',
        'Downarrow;': '\u21d3',
        'downarrow;': '\u2193',
        'DownArrowBar;': '\u2913',
        'DownArrowUpArrow;': '\u21f5',
        'DownBreve;': '\u0311',
        'downdownarrows;': '\u21ca',
        'downharpoonleft;': '\u21c3',
        'downharpoonright;': '\u21c2',
        'DownLeftRightVector;': '\u2950',
        'DownLeftTeeVector;': '\u295e',
        'DownLeftVector;': '\u21bd',
        'DownLeftVectorBar;': '\u2956',
        'DownRightTeeVector;': '\u295f',
        'DownRightVector;': '\u21c1',
        'DownRightVectorBar;': '\u2957',
        'DownTee;': '\u22a4',
        'DownTeeArrow;': '\u21a7',
        'drbkarow;': '\u2910',
        'drcorn;': '\u231f',
        'drcrop;': '\u230c',
        'Dscr;': '\U0001d49f',
        'dscr;': '\U0001d4b9',
        'DScy;': '\u0405',
        'dscy;': '\u0455',
        'dsol;': '\u29f6',
        'Dstrok;': '\u0110',
        'dstrok;': '\u0111',
        'dtdot;': '\u22f1',
        'dtri;': '\u25bf',
        'dtrif;': '\u25be',
        'duarr;': '\u21f5',
        'duhar;': '\u296f',
        'dwangle;': '\u29a6',
        'DZcy;': '\u040f',
        'dzcy;': '\u045f',
        'dzigrarr;': '\u27ff',
        'Eacute': '\xc9',
        'eacute': '\xe9',
        'Eacute;': '\xc9',
        'eacute;': '\xe9',
        'easter;': '\u2a6e',
        'Ecaron;': '\u011a',
        'ecaron;': '\u011b',
        'ecir;': '\u2256',
        'Ecirc': '\xca',
        'ecirc': '\xea',
        'Ecirc;': '\xca',
        'ecirc;': '\xea',
        'ecolon;': '\u2255',
        'Ecy;': '\u042d',
        'ecy;': '\u044d',
        'eDDot;': '\u2a77',
        'Edot;': '\u0116',
        'eDot;': '\u2251',
        'edot;': '\u0117',
        'ee;': '\u2147',
        'efDot;': '\u2252',
        'Efr;': '\U0001d508',
        'efr;': '\U0001d522',
        'eg;': '\u2a9a',
        'Egrave': '\xc8',
        'egrave': '\xe8',
        'Egrave;': '\xc8',
        'egrave;': '\xe8',
        'egs;': '\u2a96',
        'egsdot;': '\u2a98',
        'el;': '\u2a99',
        'Element;': '\u2208',
        'elinters;': '\u23e7',
        'ell;': '\u2113',
        'els;': '\u2a95',
        'elsdot;': '\u2a97',
        'Emacr;': '\u0112',
        'emacr;': '\u0113',
        'empty;': '\u2205',
        'emptyset;': '\u2205',
        'EmptySmallSquare;': '\u25fb',
        'emptyv;': '\u2205',
        'EmptyVerySmallSquare;': '\u25ab',
        'emsp13;': '\u2004',
        'emsp14;': '\u2005',
        'emsp;': '\u2003',
        'ENG;': '\u014a',
        'eng;': '\u014b',
        'ensp;': '\u2002',
        'Eogon;': '\u0118',
        'eogon;': '\u0119',
        'Eopf;': '\U0001d53c',
        'eopf;': '\U0001d556',
        'epar;': '\u22d5',
        'eparsl;': '\u29e3',
        'eplus;': '\u2a71',
        'epsi;': '\u03b5',
        'Epsilon;': '\u0395',
        'epsilon;': '\u03b5',
        'epsiv;': '\u03f5',
        'eqcirc;': '\u2256',
        'eqcolon;': '\u2255',
        'eqsim;': '\u2242',
        'eqslantgtr;': '\u2a96',
        'eqslantless;': '\u2a95',
        'Equal;': '\u2a75',
        'equals;': '=',
        'EqualTilde;': '\u2242',
        'equest;': '\u225f',
        'Equilibrium;': '\u21cc',
        'equiv;': '\u2261',
        'equivDD;': '\u2a78',
        'eqvparsl;': '\u29e5',
        'erarr;': '\u2971',
        'erDot;': '\u2253',
        'Escr;': '\u2130',
        'escr;': '\u212f',
        'esdot;': '\u2250',
        'Esim;': '\u2a73',
        'esim;': '\u2242',
        'Eta;': '\u0397',
        'eta;': '\u03b7',
        'ETH': '\xd0',
        'eth': '\xf0',
        'ETH;': '\xd0',
        'eth;': '\xf0',
        'Euml': '\xcb',
        'euml': '\xeb',
        'Euml;': '\xcb',
        'euml;': '\xeb',
        'euro;': '\u20ac',
        'excl;': '!',
        'exist;': '\u2203',
        'Exists;': '\u2203',
        'expectation;': '\u2130',
        'ExponentialE;': '\u2147',
        'exponentiale;': '\u2147',
        'fallingdotseq;': '\u2252',
        'Fcy;': '\u0424',
        'fcy;': '\u0444',
        'female;': '\u2640',
        'ffilig;': '\ufb03',
        'fflig;': '\ufb00',
        'ffllig;': '\ufb04',
        'Ffr;': '\U0001d509',
        'ffr;': '\U0001d523',
        'filig;': '\ufb01',
        'FilledSmallSquare;': '\u25fc',
        'FilledVerySmallSquare;': '\u25aa',
        'fjlig;': 'fj',
        'flat;': '\u266d',
        'fllig;': '\ufb02',
        'fltns;': '\u25b1',
        'fnof;': '\u0192',
        'Fopf;': '\U0001d53d',
        'fopf;': '\U0001d557',
        'ForAll;': '\u2200',
        'forall;': '\u2200',
        'fork;': '\u22d4',
        'forkv;': '\u2ad9',
        'Fouriertrf;': '\u2131',
        'fpartint;': '\u2a0d',
        'frac12': '\xbd',
        'frac12;': '\xbd',
        'frac13;': '\u2153',
        'frac14': '\xbc',
        'frac14;': '\xbc',
        'frac15;': '\u2155',
        'frac16;': '\u2159',
        'frac18;': '\u215b',
        'frac23;': '\u2154',
        'frac25;': '\u2156',
        'frac34': '\xbe',
        'frac34;': '\xbe',
        'frac35;': '\u2157',
        'frac38;': '\u215c',
        'frac45;': '\u2158',
        'frac56;': '\u215a',
        'frac58;': '\u215d',
        'frac78;': '\u215e',
        'frasl;': '\u2044',
        'frown;': '\u2322',
        'Fscr;': '\u2131',
        'fscr;': '\U0001d4bb',
        'gacute;': '\u01f5',
        'Gamma;': '\u0393',
        'gamma;': '\u03b3',
        'Gammad;': '\u03dc',
        'gammad;': '\u03dd',
        'gap;': '\u2a86',
        'Gbreve;': '\u011e',
        'gbreve;': '\u011f',
        'Gcedil;': '\u0122',
        'Gcirc;': '\u011c',
        'gcirc;': '\u011d',
        'Gcy;': '\u0413',
        'gcy;': '\u0433',
        'Gdot;': '\u0120',
        'gdot;': '\u0121',
        'gE;': '\u2267',
        'ge;': '\u2265',
        'gEl;': '\u2a8c',
        'gel;': '\u22db',
        'geq;': '\u2265',
        'geqq;': '\u2267',
        'geqslant;': '\u2a7e',
        'ges;': '\u2a7e',
        'gescc;': '\u2aa9',
        'gesdot;': '\u2a80',
        'gesdoto;': '\u2a82',
        'gesdotol;': '\u2a84',
        'gesl;': '\u22db\ufe00',
        'gesles;': '\u2a94',
        'Gfr;': '\U0001d50a',
        'gfr;': '\U0001d524',
        'Gg;': '\u22d9',
        'gg;': '\u226b',
        'ggg;': '\u22d9',
        'gimel;': '\u2137',
        'GJcy;': '\u0403',
        'gjcy;': '\u0453',
        'gl;': '\u2277',
        'gla;': '\u2aa5',
        'glE;': '\u2a92',
        'glj;': '\u2aa4',
        'gnap;': '\u2a8a',
        'gnapprox;': '\u2a8a',
        'gnE;': '\u2269',
        'gne;': '\u2a88',
        'gneq;': '\u2a88',
        'gneqq;': '\u2269',
        'gnsim;': '\u22e7',
        'Gopf;': '\U0001d53e',
        'gopf;': '\U0001d558',
        'grave;': '`',
        'GreaterEqual;': '\u2265',
        'GreaterEqualLess;': '\u22db',
        'GreaterFullEqual;': '\u2267',
        'GreaterGreater;': '\u2aa2',
        'GreaterLess;': '\u2277',
        'GreaterSlantEqual;': '\u2a7e',
        'GreaterTilde;': '\u2273',
        'Gscr;': '\U0001d4a2',
        'gscr;': '\u210a',
        'gsim;': '\u2273',
        'gsime;': '\u2a8e',
        'gsiml;': '\u2a90',
        'GT': '>',
        'gt': '>',
        'GT;': '>',
        'Gt;': '\u226b',
        'gt;': '>',
        'gtcc;': '\u2aa7',
        'gtcir;': '\u2a7a',
        'gtdot;': '\u22d7',
        'gtlPar;': '\u2995',
        'gtquest;': '\u2a7c',
        'gtrapprox;': '\u2a86',
        'gtrarr;': '\u2978',
        'gtrdot;': '\u22d7',
        'gtreqless;': '\u22db',
        'gtreqqless;': '\u2a8c',
        'gtrless;': '\u2277',
        'gtrsim;': '\u2273',
        'gvertneqq;': '\u2269\ufe00',
        'gvnE;': '\u2269\ufe00',
        'Hacek;': '\u02c7',
        'hairsp;': '\u200a',
        'half;': '\xbd',
        'hamilt;': '\u210b',
        'HARDcy;': '\u042a',
        'hardcy;': '\u044a',
        'hArr;': '\u21d4',
        'harr;': '\u2194',
        'harrcir;': '\u2948',
        'harrw;': '\u21ad',
        'Hat;': '^',
        'hbar;': '\u210f',
        'Hcirc;': '\u0124',
        'hcirc;': '\u0125',
        'hearts;': '\u2665',
        'heartsuit;': '\u2665',
        'hellip;': '\u2026',
        'hercon;': '\u22b9',
        'Hfr;': '\u210c',
        'hfr;': '\U0001d525',
        'HilbertSpace;': '\u210b',
        'hksearow;': '\u2925',
        'hkswarow;': '\u2926',
        'hoarr;': '\u21ff',
        'homtht;': '\u223b',
        'hookleftarrow;': '\u21a9',
        'hookrightarrow;': '\u21aa',
        'Hopf;': '\u210d',
        'hopf;': '\U0001d559',
        'horbar;': '\u2015',
        'HorizontalLine;': '\u2500',
        'Hscr;': '\u210b',
        'hscr;': '\U0001d4bd',
        'hslash;': '\u210f',
        'Hstrok;': '\u0126',
        'hstrok;': '\u0127',
        'HumpDownHump;': '\u224e',
        'HumpEqual;': '\u224f',
        'hybull;': '\u2043',
        'hyphen;': '\u2010',
        'Iacute': '\xcd',
        'iacute': '\xed',
        'Iacute;': '\xcd',
        'iacute;': '\xed',
        'ic;': '\u2063',
        'Icirc': '\xce',
        'icirc': '\xee',
        'Icirc;': '\xce',
        'icirc;': '\xee',
        'Icy;': '\u0418',
        'icy;': '\u0438',
        'Idot;': '\u0130',
        'IEcy;': '\u0415',
        'iecy;': '\u0435',
        'iexcl': '\xa1',
        'iexcl;': '\xa1',
        'iff;': '\u21d4',
        'Ifr;': '\u2111',
        'ifr;': '\U0001d526',
        'Igrave': '\xcc',
        'igrave': '\xec',
        'Igrave;': '\xcc',
        'igrave;': '\xec',
        'ii;': '\u2148',
        'iiiint;': '\u2a0c',
        'iiint;': '\u222d',
        'iinfin;': '\u29dc',
        'iiota;': '\u2129',
        'IJlig;': '\u0132',
        'ijlig;': '\u0133',
        'Im;': '\u2111',
        'Imacr;': '\u012a',
        'imacr;': '\u012b',
        'image;': '\u2111',
        'ImaginaryI;': '\u2148',
        'imagline;': '\u2110',
        'imagpart;': '\u2111',
        'imath;': '\u0131',
        'imof;': '\u22b7',
        'imped;': '\u01b5',
        'Implies;': '\u21d2',
        'in;': '\u2208',
        'incare;': '\u2105',
        'infin;': '\u221e',
        'infintie;': '\u29dd',
        'inodot;': '\u0131',
        'Int;': '\u222c',
        'int;': '\u222b',
        'intcal;': '\u22ba',
        'integers;': '\u2124',
        'Integral;': '\u222b',
        'intercal;': '\u22ba',
        'Intersection;': '\u22c2',
        'intlarhk;': '\u2a17',
        'intprod;': '\u2a3c',
        'InvisibleComma;': '\u2063',
        'InvisibleTimes;': '\u2062',
        'IOcy;': '\u0401',
        'iocy;': '\u0451',
        'Iogon;': '\u012e',
        'iogon;': '\u012f',
        'Iopf;': '\U0001d540',
        'iopf;': '\U0001d55a',
        'Iota;': '\u0399',
        'iota;': '\u03b9',
        'iprod;': '\u2a3c',
        'iquest': '\xbf',
        'iquest;': '\xbf',
        'Iscr;': '\u2110',
        'iscr;': '\U0001d4be',
        'isin;': '\u2208',
        'isindot;': '\u22f5',
        'isinE;': '\u22f9',
        'isins;': '\u22f4',
        'isinsv;': '\u22f3',
        'isinv;': '\u2208',
        'it;': '\u2062',
        'Itilde;': '\u0128',
        'itilde;': '\u0129',
        'Iukcy;': '\u0406',
        'iukcy;': '\u0456',
        'Iuml': '\xcf',
        'iuml': '\xef',
        'Iuml;': '\xcf',
        'iuml;': '\xef',
        'Jcirc;': '\u0134',
        'jcirc;': '\u0135',
        'Jcy;': '\u0419',
        'jcy;': '\u0439',
        'Jfr;': '\U0001d50d',
        'jfr;': '\U0001d527',
        'jmath;': '\u0237',
        'Jopf;': '\U0001d541',
        'jopf;': '\U0001d55b',
        'Jscr;': '\U0001d4a5',
        'jscr;': '\U0001d4bf',
        'Jsercy;': '\u0408',
        'jsercy;': '\u0458',
        'Jukcy;': '\u0404',
        'jukcy;': '\u0454',
        'Kappa;': '\u039a',
        'kappa;': '\u03ba',
        'kappav;': '\u03f0',
        'Kcedil;': '\u0136',
        'kcedil;': '\u0137',
        'Kcy;': '\u041a',
        'kcy;': '\u043a',
        'Kfr;': '\U0001d50e',
        'kfr;': '\U0001d528',
        'kgreen;': '\u0138',
        'KHcy;': '\u0425',
        'khcy;': '\u0445',
        'KJcy;': '\u040c',
        'kjcy;': '\u045c',
        'Kopf;': '\U0001d542',
        'kopf;': '\U0001d55c',
        'Kscr;': '\U0001d4a6',
        'kscr;': '\U0001d4c0',
        'lAarr;': '\u21da',
        'Lacute;': '\u0139',
        'lacute;': '\u013a',
        'laemptyv;': '\u29b4',
        'lagran;': '\u2112',
        'Lambda;': '\u039b',
        'lambda;': '\u03bb',
        'Lang;': '\u27ea',
        'lang;': '\u27e8',
        'langd;': '\u2991',
        'langle;': '\u27e8',
        'lap;': '\u2a85',
        'Laplacetrf;': '\u2112',
        'laquo': '\xab',
        'laquo;': '\xab',
        'Larr;': '\u219e',
        'lArr;': '\u21d0',
        'larr;': '\u2190',
        'larrb;': '\u21e4',
        'larrbfs;': '\u291f',
        'larrfs;': '\u291d',
        'larrhk;': '\u21a9',
        'larrlp;': '\u21ab',
        'larrpl;': '\u2939',
        'larrsim;': '\u2973',
        'larrtl;': '\u21a2',
        'lat;': '\u2aab',
        'lAtail;': '\u291b',
        'latail;': '\u2919',
        'late;': '\u2aad',
        'lates;': '\u2aad\ufe00',
        'lBarr;': '\u290e',
        'lbarr;': '\u290c',
        'lbbrk;': '\u2772',
        'lbrace;': '{',
        'lbrack;': '[',
        'lbrke;': '\u298b',
        'lbrksld;': '\u298f',
        'lbrkslu;': '\u298d',
        'Lcaron;': '\u013d',
        'lcaron;': '\u013e',
        'Lcedil;': '\u013b',
        'lcedil;': '\u013c',
        'lceil;': '\u2308',
        'lcub;': '{',
        'Lcy;': '\u041b',
        'lcy;': '\u043b',
        'ldca;': '\u2936',
        'ldquo;': '\u201c',
        'ldquor;': '\u201e',
        'ldrdhar;': '\u2967',
        'ldrushar;': '\u294b',
        'ldsh;': '\u21b2',
        'lE;': '\u2266',
        'le;': '\u2264',
        'LeftAngleBracket;': '\u27e8',
        'LeftArrow;': '\u2190',
        'Leftarrow;': '\u21d0',
        'leftarrow;': '\u2190',
        'LeftArrowBar;': '\u21e4',
        'LeftArrowRightArrow;': '\u21c6',
        'leftarrowtail;': '\u21a2',
        'LeftCeiling;': '\u2308',
        'LeftDoubleBracket;': '\u27e6',
        'LeftDownTeeVector;': '\u2961',
        'LeftDownVector;': '\u21c3',
        'LeftDownVectorBar;': '\u2959',
        'LeftFloor;': '\u230a',
        'leftharpoondown;': '\u21bd',
        'leftharpoonup;': '\u21bc',
        'leftleftarrows;': '\u21c7',
        'LeftRightArrow;': '\u2194',
        'Leftrightarrow;': '\u21d4',
        'leftrightarrow;': '\u2194',
        'leftrightarrows;': '\u21c6',
        'leftrightharpoons;': '\u21cb',
        'leftrightsquigarrow;': '\u21ad',
        'LeftRightVector;': '\u294e',
        'LeftTee;': '\u22a3',
        'LeftTeeArrow;': '\u21a4',
        'LeftTeeVector;': '\u295a',
        'leftthreetimes;': '\u22cb',
        'LeftTriangle;': '\u22b2',
        'LeftTriangleBar;': '\u29cf',
        'LeftTriangleEqual;': '\u22b4',
        'LeftUpDownVector;': '\u2951',
        'LeftUpTeeVector;': '\u2960',
        'LeftUpVector;': '\u21bf',
        'LeftUpVectorBar;': '\u2958',
        'LeftVector;': '\u21bc',
        'LeftVectorBar;': '\u2952',
        'lEg;': '\u2a8b',
        'leg;': '\u22da',
        'leq;': '\u2264',
        'leqq;': '\u2266',
        'leqslant;': '\u2a7d',
        'les;': '\u2a7d',
        'lescc;': '\u2aa8',
        'lesdot;': '\u2a7f',
        'lesdoto;': '\u2a81',
        'lesdotor;': '\u2a83',
        'lesg;': '\u22da\ufe00',
        'lesges;': '\u2a93',
        'lessapprox;': '\u2a85',
        'lessdot;': '\u22d6',
        'lesseqgtr;': '\u22da',
        'lesseqqgtr;': '\u2a8b',
        'LessEqualGreater;': '\u22da',
        'LessFullEqual;': '\u2266',
        'LessGreater;': '\u2276',
        'lessgtr;': '\u2276',
        'LessLess;': '\u2aa1',
        'lesssim;': '\u2272',
        'LessSlantEqual;': '\u2a7d',
        'LessTilde;': '\u2272',
        'lfisht;': '\u297c',
        'lfloor;': '\u230a',
        'Lfr;': '\U0001d50f',
        'lfr;': '\U0001d529',
        'lg;': '\u2276',
        'lgE;': '\u2a91',
        'lHar;': '\u2962',
        'lhard;': '\u21bd',
        'lharu;': '\u21bc',
        'lharul;': '\u296a',
        'lhblk;': '\u2584',
        'LJcy;': '\u0409',
        'ljcy;': '\u0459',
        'Ll;': '\u22d8',
        'll;': '\u226a',
        'llarr;': '\u21c7',
        'llcorner;': '\u231e',
        'Lleftarrow;': '\u21da',
        'llhard;': '\u296b',
        'lltri;': '\u25fa',
        'Lmidot;': '\u013f',
        'lmidot;': '\u0140',
        'lmoust;': '\u23b0',
        'lmoustache;': '\u23b0',
        'lnap;': '\u2a89',
        'lnapprox;': '\u2a89',
        'lnE;': '\u2268',
        'lne;': '\u2a87',
        'lneq;': '\u2a87',
        'lneqq;': '\u2268',
        'lnsim;': '\u22e6',
        'loang;': '\u27ec',
        'loarr;': '\u21fd',
        'lobrk;': '\u27e6',
        'LongLeftArrow;': '\u27f5',
        'Longleftarrow;': '\u27f8',
        'longleftarrow;': '\u27f5',
        'LongLeftRightArrow;': '\u27f7',
        'Longleftrightarrow;': '\u27fa',
        'longleftrightarrow;': '\u27f7',
        'longmapsto;': '\u27fc',
        'LongRightArrow;': '\u27f6',
        'Longrightarrow;': '\u27f9',
        'longrightarrow;': '\u27f6',
        'looparrowleft;': '\u21ab',
        'looparrowright;': '\u21ac',
        'lopar;': '\u2985',
        'Lopf;': '\U0001d543',
        'lopf;': '\U0001d55d',
        'loplus;': '\u2a2d',
        'lotimes;': '\u2a34',
        'lowast;': '\u2217',
        'lowbar;': '_',
        'LowerLeftArrow;': '\u2199',
        'LowerRightArrow;': '\u2198',
        'loz;': '\u25ca',
        'lozenge;': '\u25ca',
        'lozf;': '\u29eb',
        'lpar;': '(',
        'lparlt;': '\u2993',
        'lrarr;': '\u21c6',
        'lrcorner;': '\u231f',
        'lrhar;': '\u21cb',
        'lrhard;': '\u296d',
        'lrm;': '\u200e',
        'lrtri;': '\u22bf',
        'lsaquo;': '\u2039',
        'Lscr;': '\u2112',
        'lscr;': '\U0001d4c1',
        'Lsh;': '\u21b0',
        'lsh;': '\u21b0',
        'lsim;': '\u2272',
        'lsime;': '\u2a8d',
        'lsimg;': '\u2a8f',
        'lsqb;': '[',
        'lsquo;': '\u2018',
        'lsquor;': '\u201a',
        'Lstrok;': '\u0141',
        'lstrok;': '\u0142',
        'LT': '<',
        'lt': '<',
        'LT;': '<',
        'Lt;': '\u226a',
        'lt;': '<',
        'ltcc;': '\u2aa6',
        'ltcir;': '\u2a79',
        'ltdot;': '\u22d6',
        'lthree;': '\u22cb',
        'ltimes;': '\u22c9',
        'ltlarr;': '\u2976',
        'ltquest;': '\u2a7b',
        'ltri;': '\u25c3',
        'ltrie;': '\u22b4',
        'ltrif;': '\u25c2',
        'ltrPar;': '\u2996',
        'lurdshar;': '\u294a',
        'luruhar;': '\u2966',
        'lvertneqq;': '\u2268\ufe00',
        'lvnE;': '\u2268\ufe00',
        'macr': '\xaf',
        'macr;': '\xaf',
        'male;': '\u2642',
        'malt;': '\u2720',
        'maltese;': '\u2720',
        'Map;': '\u2905',
        'map;': '\u21a6',
        'mapsto;': '\u21a6',
        'mapstodown;': '\u21a7',
        'mapstoleft;': '\u21a4',
        'mapstoup;': '\u21a5',
        'marker;': '\u25ae',
        'mcomma;': '\u2a29',
        'Mcy;': '\u041c',
        'mcy;': '\u043c',
        'mdash;': '\u2014',
        'mDDot;': '\u223a',
        'measuredangle;': '\u2221',
        'MediumSpace;': '\u205f',
        'Mellintrf;': '\u2133',
        'Mfr;': '\U0001d510',
        'mfr;': '\U0001d52a',
        'mho;': '\u2127',
        'micro': '\xb5',
        'micro;': '\xb5',
        'mid;': '\u2223',
        'midast;': '*',
        'midcir;': '\u2af0',
        'middot': '\xb7',
        'middot;': '\xb7',
        'minus;': '\u2212',
        'minusb;': '\u229f',
        'minusd;': '\u2238',
        'minusdu;': '\u2a2a',
        'MinusPlus;': '\u2213',
        'mlcp;': '\u2adb',
        'mldr;': '\u2026',
        'mnplus;': '\u2213',
        'models;': '\u22a7',
        'Mopf;': '\U0001d544',
        'mopf;': '\U0001d55e',
        'mp;': '\u2213',
        'Mscr;': '\u2133',
        'mscr;': '\U0001d4c2',
        'mstpos;': '\u223e',
        'Mu;': '\u039c',
        'mu;': '\u03bc',
        'multimap;': '\u22b8',
        'mumap;': '\u22b8',
        'nabla;': '\u2207',
        'Nacute;': '\u0143',
        'nacute;': '\u0144',
        'nang;': '\u2220\u20d2',
        'nap;': '\u2249',
        'napE;': '\u2a70\u0338',
        'napid;': '\u224b\u0338',
        'napos;': '\u0149',
        'napprox;': '\u2249',
        'natur;': '\u266e',
        'natural;': '\u266e',
        'naturals;': '\u2115',
        'nbsp': '\xa0',
        'nbsp;': '\xa0',
        'nbump;': '\u224e\u0338',
        'nbumpe;': '\u224f\u0338',
        'ncap;': '\u2a43',
        'Ncaron;': '\u0147',
        'ncaron;': '\u0148',
        'Ncedil;': '\u0145',
        'ncedil;': '\u0146',
        'ncong;': '\u2247',
        'ncongdot;': '\u2a6d\u0338',
        'ncup;': '\u2a42',
        'Ncy;': '\u041d',
        'ncy;': '\u043d',
        'ndash;': '\u2013',
        'ne;': '\u2260',
        'nearhk;': '\u2924',
        'neArr;': '\u21d7',
        'nearr;': '\u2197',
        'nearrow;': '\u2197',
        'nedot;': '\u2250\u0338',
        'NegativeMediumSpace;': '\u200b',
        'NegativeThickSpace;': '\u200b',
        'NegativeThinSpace;': '\u200b',
        'NegativeVeryThinSpace;': '\u200b',
        'nequiv;': '\u2262',
        'nesear;': '\u2928',
        'nesim;': '\u2242\u0338',
        'NestedGreaterGreater;': '\u226b',
        'NestedLessLess;': '\u226a',
        'NewLine;': '\n',
        'nexist;': '\u2204',
        'nexists;': '\u2204',
        'Nfr;': '\U0001d511',
        'nfr;': '\U0001d52b',
        'ngE;': '\u2267\u0338',
        'nge;': '\u2271',
        'ngeq;': '\u2271',
        'ngeqq;': '\u2267\u0338',
        'ngeqslant;': '\u2a7e\u0338',
        'nges;': '\u2a7e\u0338',
        'nGg;': '\u22d9\u0338',
        'ngsim;': '\u2275',
        'nGt;': '\u226b\u20d2',
        'ngt;': '\u226f',
        'ngtr;': '\u226f',
        'nGtv;': '\u226b\u0338',
        'nhArr;': '\u21ce',
        'nharr;': '\u21ae',
        'nhpar;': '\u2af2',
        'ni;': '\u220b',
        'nis;': '\u22fc',
        'nisd;': '\u22fa',
        'niv;': '\u220b',
        'NJcy;': '\u040a',
        'njcy;': '\u045a',
        'nlArr;': '\u21cd',
        'nlarr;': '\u219a',
        'nldr;': '\u2025',
        'nlE;': '\u2266\u0338',
        'nle;': '\u2270',
        'nLeftarrow;': '\u21cd',
        'nleftarrow;': '\u219a',
        'nLeftrightarrow;': '\u21ce',
        'nleftrightarrow;': '\u21ae',
        'nleq;': '\u2270',
        'nleqq;': '\u2266\u0338',
        'nleqslant;': '\u2a7d\u0338',
        'nles;': '\u2a7d\u0338',
        'nless;': '\u226e',
        'nLl;': '\u22d8\u0338',
        'nlsim;': '\u2274',
        'nLt;': '\u226a\u20d2',
        'nlt;': '\u226e',
        'nltri;': '\u22ea',
        'nltrie;': '\u22ec',
        'nLtv;': '\u226a\u0338',
        'nmid;': '\u2224',
        'NoBreak;': '\u2060',
        'NonBreakingSpace;': '\xa0',
        'Nopf;': '\u2115',
        'nopf;': '\U0001d55f',
        'not': '\xac',
        'Not;': '\u2aec',
        'not;': '\xac',
        'NotCongruent;': '\u2262',
        'NotCupCap;': '\u226d',
        'NotDoubleVerticalBar;': '\u2226',
        'NotElement;': '\u2209',
        'NotEqual;': '\u2260',
        'NotEqualTilde;': '\u2242\u0338',
        'NotExists;': '\u2204',
        'NotGreater;': '\u226f',
        'NotGreaterEqual;': '\u2271',
        'NotGreaterFullEqual;': '\u2267\u0338',
        'NotGreaterGreater;': '\u226b\u0338',
        'NotGreaterLess;': '\u2279',
        'NotGreaterSlantEqual;': '\u2a7e\u0338',
        'NotGreaterTilde;': '\u2275',
        'NotHumpDownHump;': '\u224e\u0338',
        'NotHumpEqual;': '\u224f\u0338',
        'notin;': '\u2209',
        'notindot;': '\u22f5\u0338',
        'notinE;': '\u22f9\u0338',
        'notinva;': '\u2209',
        'notinvb;': '\u22f7',
        'notinvc;': '\u22f6',
        'NotLeftTriangle;': '\u22ea',
        'NotLeftTriangleBar;': '\u29cf\u0338',
        'NotLeftTriangleEqual;': '\u22ec',
        'NotLess;': '\u226e',
        'NotLessEqual;': '\u2270',
        'NotLessGreater;': '\u2278',
        'NotLessLess;': '\u226a\u0338',
        'NotLessSlantEqual;': '\u2a7d\u0338',
        'NotLessTilde;': '\u2274',
        'NotNestedGreaterGreater;': '\u2aa2\u0338',
        'NotNestedLessLess;': '\u2aa1\u0338',
        'notni;': '\u220c',
        'notniva;': '\u220c',
        'notnivb;': '\u22fe',
        'notnivc;': '\u22fd',
        'NotPrecedes;': '\u2280',
        'NotPrecedesEqual;': '\u2aaf\u0338',
        'NotPrecedesSlantEqual;': '\u22e0',
        'NotReverseElement;': '\u220c',
        'NotRightTriangle;': '\u22eb',
        'NotRightTriangleBar;': '\u29d0\u0338',
        'NotRightTriangleEqual;': '\u22ed',
        'NotSquareSubset;': '\u228f\u0338',
        'NotSquareSubsetEqual;': '\u22e2',
        'NotSquareSuperset;': '\u2290\u0338',
        'NotSquareSupersetEqual;': '\u22e3',
        'NotSubset;': '\u2282\u20d2',
        'NotSubsetEqual;': '\u2288',
        'NotSucceeds;': '\u2281',
        'NotSucceedsEqual;': '\u2ab0\u0338',
        'NotSucceedsSlantEqual;': '\u22e1',
        'NotSucceedsTilde;': '\u227f\u0338',
        'NotSuperset;': '\u2283\u20d2',
        'NotSupersetEqual;': '\u2289',
        'NotTilde;': '\u2241',
        'NotTildeEqual;': '\u2244',
        'NotTildeFullEqual;': '\u2247',
        'NotTildeTilde;': '\u2249',
        'NotVerticalBar;': '\u2224',
        'npar;': '\u2226',
        'nparallel;': '\u2226',
        'nparsl;': '\u2afd\u20e5',
        'npart;': '\u2202\u0338',
        'npolint;': '\u2a14',
        'npr;': '\u2280',
        'nprcue;': '\u22e0',
        'npre;': '\u2aaf\u0338',
        'nprec;': '\u2280',
        'npreceq;': '\u2aaf\u0338',
        'nrArr;': '\u21cf',
        'nrarr;': '\u219b',
        'nrarrc;': '\u2933\u0338',
        'nrarrw;': '\u219d\u0338',
        'nRightarrow;': '\u21cf',
        'nrightarrow;': '\u219b',
        'nrtri;': '\u22eb',
        'nrtrie;': '\u22ed',
        'nsc;': '\u2281',
        'nsccue;': '\u22e1',
        'nsce;': '\u2ab0\u0338',
        'Nscr;': '\U0001d4a9',
        'nscr;': '\U0001d4c3',
        'nshortmid;': '\u2224',
        'nshortparallel;': '\u2226',
        'nsim;': '\u2241',
        'nsime;': '\u2244',
        'nsimeq;': '\u2244',
        'nsmid;': '\u2224',
        'nspar;': '\u2226',
        'nsqsube;': '\u22e2',
        'nsqsupe;': '\u22e3',
        'nsub;': '\u2284',
        'nsubE;': '\u2ac5\u0338',
        'nsube;': '\u2288',
        'nsubset;': '\u2282\u20d2',
        'nsubseteq;': '\u2288',
        'nsubseteqq;': '\u2ac5\u0338',
        'nsucc;': '\u2281',
        'nsucceq;': '\u2ab0\u0338',
        'nsup;': '\u2285',
        'nsupE;': '\u2ac6\u0338',
        'nsupe;': '\u2289',
        'nsupset;': '\u2283\u20d2',
        'nsupseteq;': '\u2289',
        'nsupseteqq;': '\u2ac6\u0338',
        'ntgl;': '\u2279',
        'Ntilde': '\xd1',
        'ntilde': '\xf1',
        'Ntilde;': '\xd1',
        'ntilde;': '\xf1',
        'ntlg;': '\u2278',
        'ntriangleleft;': '\u22ea',
        'ntrianglelefteq;': '\u22ec',
        'ntriangleright;': '\u22eb',
        'ntrianglerighteq;': '\u22ed',
        'Nu;': '\u039d',
        'nu;': '\u03bd',
        'num;': '#',
        'numero;': '\u2116',
        'numsp;': '\u2007',
        'nvap;': '\u224d\u20d2',
        'nVDash;': '\u22af',
        'nVdash;': '\u22ae',
        'nvDash;': '\u22ad',
        'nvdash;': '\u22ac',
        'nvge;': '\u2265\u20d2',
        'nvgt;': '>\u20d2',
        'nvHarr;': '\u2904',
        'nvinfin;': '\u29de',
        'nvlArr;': '\u2902',
        'nvle;': '\u2264\u20d2',
        'nvlt;': '<\u20d2',
        'nvltrie;': '\u22b4\u20d2',
        'nvrArr;': '\u2903',
        'nvrtrie;': '\u22b5\u20d2',
        'nvsim;': '\u223c\u20d2',
        'nwarhk;': '\u2923',
        'nwArr;': '\u21d6',
        'nwarr;': '\u2196',
        'nwarrow;': '\u2196',
        'nwnear;': '\u2927',
        'Oacute': '\xd3',
        'oacute': '\xf3',
        'Oacute;': '\xd3',
        'oacute;': '\xf3',
        'oast;': '\u229b',
        'ocir;': '\u229a',
        'Ocirc': '\xd4',
        'ocirc': '\xf4',
        'Ocirc;': '\xd4',
        'ocirc;': '\xf4',
        'Ocy;': '\u041e',
        'ocy;': '\u043e',
        'odash;': '\u229d',
        'Odblac;': '\u0150',
        'odblac;': '\u0151',
        'odiv;': '\u2a38',
        'odot;': '\u2299',
        'odsold;': '\u29bc',
        'OElig;': '\u0152',
        'oelig;': '\u0153',
        'ofcir;': '\u29bf',
        'Ofr;': '\U0001d512',
        'ofr;': '\U0001d52c',
        'ogon;': '\u02db',
        'Ograve': '\xd2',
        'ograve': '\xf2',
        'Ograve;': '\xd2',
        'ograve;': '\xf2',
        'ogt;': '\u29c1',
        'ohbar;': '\u29b5',
        'ohm;': '\u03a9',
        'oint;': '\u222e',
        'olarr;': '\u21ba',
        'olcir;': '\u29be',
        'olcross;': '\u29bb',
        'oline;': '\u203e',
        'olt;': '\u29c0',
        'Omacr;': '\u014c',
        'omacr;': '\u014d',
        'Omega;': '\u03a9',
        'omega;': '\u03c9',
        'Omicron;': '\u039f',
        'omicron;': '\u03bf',
        'omid;': '\u29b6',
        'ominus;': '\u2296',
        'Oopf;': '\U0001d546',
        'oopf;': '\U0001d560',
        'opar;': '\u29b7',
        'OpenCurlyDoubleQuote;': '\u201c',
        'OpenCurlyQuote;': '\u2018',
        'operp;': '\u29b9',
        'oplus;': '\u2295',
        'Or;': '\u2a54',
        'or;': '\u2228',
        'orarr;': '\u21bb',
        'ord;': '\u2a5d',
        'order;': '\u2134',
        'orderof;': '\u2134',
        'ordf': '\xaa',
        'ordf;': '\xaa',
        'ordm': '\xba',
        'ordm;': '\xba',
        'origof;': '\u22b6',
        'oror;': '\u2a56',
        'orslope;': '\u2a57',
        'orv;': '\u2a5b',
        'oS;': '\u24c8',
        'Oscr;': '\U0001d4aa',
        'oscr;': '\u2134',
        'Oslash': '\xd8',
        'oslash': '\xf8',
        'Oslash;': '\xd8',
        'oslash;': '\xf8',
        'osol;': '\u2298',
        'Otilde': '\xd5',
        'otilde': '\xf5',
        'Otilde;': '\xd5',
        'otilde;': '\xf5',
        'Otimes;': '\u2a37',
        'otimes;': '\u2297',
        'otimesas;': '\u2a36',
        'Ouml': '\xd6',
        'ouml': '\xf6',
        'Ouml;': '\xd6',
        'ouml;': '\xf6',
        'ovbar;': '\u233d',
        'OverBar;': '\u203e',
        'OverBrace;': '\u23de',
        'OverBracket;': '\u23b4',
        'OverParenthesis;': '\u23dc',
        'par;': '\u2225',
        'para': '\xb6',
        'para;': '\xb6',
        'parallel;': '\u2225',
        'parsim;': '\u2af3',
        'parsl;': '\u2afd',
        'part;': '\u2202',
        'PartialD;': '\u2202',
        'Pcy;': '\u041f',
        'pcy;': '\u043f',
        'percnt;': '%',
        'period;': '.',
        'permil;': '\u2030',
        'perp;': '\u22a5',
        'pertenk;': '\u2031',
        'Pfr;': '\U0001d513',
        'pfr;': '\U0001d52d',
        'Phi;': '\u03a6',
        'phi;': '\u03c6',
        'phiv;': '\u03d5',
        'phmmat;': '\u2133',
        'phone;': '\u260e',
        'Pi;': '\u03a0',
        'pi;': '\u03c0',
        'pitchfork;': '\u22d4',
        'piv;': '\u03d6',
        'planck;': '\u210f',
        'planckh;': '\u210e',
        'plankv;': '\u210f',
        'plus;': '+',
        'plusacir;': '\u2a23',
        'plusb;': '\u229e',
        'pluscir;': '\u2a22',
        'plusdo;': '\u2214',
        'plusdu;': '\u2a25',
        'pluse;': '\u2a72',
        'PlusMinus;': '\xb1',
        'plusmn': '\xb1',
        'plusmn;': '\xb1',
        'plussim;': '\u2a26',
        'plustwo;': '\u2a27',
        'pm;': '\xb1',
        'Poincareplane;': '\u210c',
        'pointint;': '\u2a15',
        'Popf;': '\u2119',
        'popf;': '\U0001d561',
        'pound': '\xa3',
        'pound;': '\xa3',
        'Pr;': '\u2abb',
        'pr;': '\u227a',
        'prap;': '\u2ab7',
        'prcue;': '\u227c',
        'prE;': '\u2ab3',
        'pre;': '\u2aaf',
        'prec;': '\u227a',
        'precapprox;': '\u2ab7',
        'preccurlyeq;': '\u227c',
        'Precedes;': '\u227a',
        'PrecedesEqual;': '\u2aaf',
        'PrecedesSlantEqual;': '\u227c',
        'PrecedesTilde;': '\u227e',
        'preceq;': '\u2aaf',
        'precnapprox;': '\u2ab9',
        'precneqq;': '\u2ab5',
        'precnsim;': '\u22e8',
        'precsim;': '\u227e',
        'Prime;': '\u2033',
        'prime;': '\u2032',
        'primes;': '\u2119',
        'prnap;': '\u2ab9',
        'prnE;': '\u2ab5',
        'prnsim;': '\u22e8',
        'prod;': '\u220f',
        'Product;': '\u220f',
        'profalar;': '\u232e',
        'profline;': '\u2312',
        'profsurf;': '\u2313',
        'prop;': '\u221d',
        'Proportion;': '\u2237',
        'Proportional;': '\u221d',
        'propto;': '\u221d',
        'prsim;': '\u227e',
        'prurel;': '\u22b0',
        'Pscr;': '\U0001d4ab',
        'pscr;': '\U0001d4c5',
        'Psi;': '\u03a8',
        'psi;': '\u03c8',
        'puncsp;': '\u2008',
        'Qfr;': '\U0001d514',
        'qfr;': '\U0001d52e',
        'qint;': '\u2a0c',
        'Qopf;': '\u211a',
        'qopf;': '\U0001d562',
        'qprime;': '\u2057',
        'Qscr;': '\U0001d4ac',
        'qscr;': '\U0001d4c6',
        'quaternions;': '\u210d',
        'quatint;': '\u2a16',
        'quest;': '?',
        'questeq;': '\u225f',
        'QUOT': '"',
        'quot': '"',
        'QUOT;': '"',
        'quot;': '"',
        'rAarr;': '\u21db',
        'race;': '\u223d\u0331',
        'Racute;': '\u0154',
        'racute;': '\u0155',
        'radic;': '\u221a',
        'raemptyv;': '\u29b3',
        'Rang;': '\u27eb',
        'rang;': '\u27e9',
        'rangd;': '\u2992',
        'range;': '\u29a5',
        'rangle;': '\u27e9',
        'raquo': '\xbb',
        'raquo;': '\xbb',
        'Rarr;': '\u21a0',
        'rArr;': '\u21d2',
        'rarr;': '\u2192',
        'rarrap;': '\u2975',
        'rarrb;': '\u21e5',
        'rarrbfs;': '\u2920',
        'rarrc;': '\u2933',
        'rarrfs;': '\u291e',
        'rarrhk;': '\u21aa',
        'rarrlp;': '\u21ac',
        'rarrpl;': '\u2945',
        'rarrsim;': '\u2974',
        'Rarrtl;': '\u2916',
        'rarrtl;': '\u21a3',
        'rarrw;': '\u219d',
        'rAtail;': '\u291c',
        'ratail;': '\u291a',
        'ratio;': '\u2236',
        'rationals;': '\u211a',
        'RBarr;': '\u2910',
        'rBarr;': '\u290f',
        'rbarr;': '\u290d',
        'rbbrk;': '\u2773',
        'rbrace;': '}',
        'rbrack;': ']',
        'rbrke;': '\u298c',
        'rbrksld;': '\u298e',
        'rbrkslu;': '\u2990',
        'Rcaron;': '\u0158',
        'rcaron;': '\u0159',
        'Rcedil;': '\u0156',
        'rcedil;': '\u0157',
        'rceil;': '\u2309',
        'rcub;': '}',
        'Rcy;': '\u0420',
        'rcy;': '\u0440',
        'rdca;': '\u2937',
        'rdldhar;': '\u2969',
        'rdquo;': '\u201d',
        'rdquor;': '\u201d',
        'rdsh;': '\u21b3',
        'Re;': '\u211c',
        'real;': '\u211c',
        'realine;': '\u211b',
        'realpart;': '\u211c',
        'reals;': '\u211d',
        'rect;': '\u25ad',
        'REG': '\xae',
        'reg': '\xae',
        'REG;': '\xae',
        'reg;': '\xae',
        'ReverseElement;': '\u220b',
        'ReverseEquilibrium;': '\u21cb',
        'ReverseUpEquilibrium;': '\u296f',
        'rfisht;': '\u297d',
        'rfloor;': '\u230b',
        'Rfr;': '\u211c',
        'rfr;': '\U0001d52f',
        'rHar;': '\u2964',
        'rhard;': '\u21c1',
        'rharu;': '\u21c0',
        'rharul;': '\u296c',
        'Rho;': '\u03a1',
        'rho;': '\u03c1',
        'rhov;': '\u03f1',
        'RightAngleBracket;': '\u27e9',
        'RightArrow;': '\u2192',
        'Rightarrow;': '\u21d2',
        'rightarrow;': '\u2192',
        'RightArrowBar;': '\u21e5',
        'RightArrowLeftArrow;': '\u21c4',
        'rightarrowtail;': '\u21a3',
        'RightCeiling;': '\u2309',
        'RightDoubleBracket;': '\u27e7',
        'RightDownTeeVector;': '\u295d',
        'RightDownVector;': '\u21c2',
        'RightDownVectorBar;': '\u2955',
        'RightFloor;': '\u230b',
        'rightharpoondown;': '\u21c1',
        'rightharpoonup;': '\u21c0',
        'rightleftarrows;': '\u21c4',
        'rightleftharpoons;': '\u21cc',
        'rightrightarrows;': '\u21c9',
        'rightsquigarrow;': '\u219d',
        'RightTee;': '\u22a2',
        'RightTeeArrow;': '\u21a6',
        'RightTeeVector;': '\u295b',
        'rightthreetimes;': '\u22cc',
        'RightTriangle;': '\u22b3',
        'RightTriangleBar;': '\u29d0',
        'RightTriangleEqual;': '\u22b5',
        'RightUpDownVector;': '\u294f',
        'RightUpTeeVector;': '\u295c',
        'RightUpVector;': '\u21be',
        'RightUpVectorBar;': '\u2954',
        'RightVector;': '\u21c0',
        'RightVectorBar;': '\u2953',
        'ring;': '\u02da',
        'risingdotseq;': '\u2253',
        'rlarr;': '\u21c4',
        'rlhar;': '\u21cc',
        'rlm;': '\u200f',
        'rmoust;': '\u23b1',
        'rmoustache;': '\u23b1',
        'rnmid;': '\u2aee',
        'roang;': '\u27ed',
        'roarr;': '\u21fe',
        'robrk;': '\u27e7',
        'ropar;': '\u2986',
        'Ropf;': '\u211d',
        'ropf;': '\U0001d563',
        'roplus;': '\u2a2e',
        'rotimes;': '\u2a35',
        'RoundImplies;': '\u2970',
        'rpar;': ')',
        'rpargt;': '\u2994',
        'rppolint;': '\u2a12',
        'rrarr;': '\u21c9',
        'Rrightarrow;': '\u21db',
        'rsaquo;': '\u203a',
        'Rscr;': '\u211b',
        'rscr;': '\U0001d4c7',
        'Rsh;': '\u21b1',
        'rsh;': '\u21b1',
        'rsqb;': ']',
        'rsquo;': '\u2019',
        'rsquor;': '\u2019',
        'rthree;': '\u22cc',
        'rtimes;': '\u22ca',
        'rtri;': '\u25b9',
        'rtrie;': '\u22b5',
        'rtrif;': '\u25b8',
        'rtriltri;': '\u29ce',
        'RuleDelayed;': '\u29f4',
        'ruluhar;': '\u2968',
        'rx;': '\u211e',
        'Sacute;': '\u015a',
        'sacute;': '\u015b',
        'sbquo;': '\u201a',
        'Sc;': '\u2abc',
        'sc;': '\u227b',
        'scap;': '\u2ab8',
        'Scaron;': '\u0160',
        'scaron;': '\u0161',
        'sccue;': '\u227d',
        'scE;': '\u2ab4',
        'sce;': '\u2ab0',
        'Scedil;': '\u015e',
        'scedil;': '\u015f',
        'Scirc;': '\u015c',
        'scirc;': '\u015d',
        'scnap;': '\u2aba',
        'scnE;': '\u2ab6',
        'scnsim;': '\u22e9',
        'scpolint;': '\u2a13',
        'scsim;': '\u227f',
        'Scy;': '\u0421',
        'scy;': '\u0441',
        'sdot;': '\u22c5',
        'sdotb;': '\u22a1',
        'sdote;': '\u2a66',
        'searhk;': '\u2925',
        'seArr;': '\u21d8',
        'searr;': '\u2198',
        'searrow;': '\u2198',
        'sect': '\xa7',
        'sect;': '\xa7',
        'semi;': ';',
        'seswar;': '\u2929',
        'setminus;': '\u2216',
        'setmn;': '\u2216',
        'sext;': '\u2736',
        'Sfr;': '\U0001d516',
        'sfr;': '\U0001d530',
        'sfrown;': '\u2322',
        'sharp;': '\u266f',
        'SHCHcy;': '\u0429',
        'shchcy;': '\u0449',
        'SHcy;': '\u0428',
        'shcy;': '\u0448',
        'ShortDownArrow;': '\u2193',
        'ShortLeftArrow;': '\u2190',
        'shortmid;': '\u2223',
        'shortparallel;': '\u2225',
        'ShortRightArrow;': '\u2192',
        'ShortUpArrow;': '\u2191',
        'shy': '\xad',
        'shy;': '\xad',
        'Sigma;': '\u03a3',
        'sigma;': '\u03c3',
        'sigmaf;': '\u03c2',
        'sigmav;': '\u03c2',
        'sim;': '\u223c',
        'simdot;': '\u2a6a',
        'sime;': '\u2243',
        'simeq;': '\u2243',
        'simg;': '\u2a9e',
        'simgE;': '\u2aa0',
        'siml;': '\u2a9d',
        'simlE;': '\u2a9f',
        'simne;': '\u2246',
        'simplus;': '\u2a24',
        'simrarr;': '\u2972',
        'slarr;': '\u2190',
        'SmallCircle;': '\u2218',
        'smallsetminus;': '\u2216',
        'smashp;': '\u2a33',
        'smeparsl;': '\u29e4',
        'smid;': '\u2223',
        'smile;': '\u2323',
        'smt;': '\u2aaa',
        'smte;': '\u2aac',
        'smtes;': '\u2aac\ufe00',
        'SOFTcy;': '\u042c',
        'softcy;': '\u044c',
        'sol;': '/',
        'solb;': '\u29c4',
        'solbar;': '\u233f',
        'Sopf;': '\U0001d54a',
        'sopf;': '\U0001d564',
        'spades;': '\u2660',
        'spadesuit;': '\u2660',
        'spar;': '\u2225',
        'sqcap;': '\u2293',
        'sqcaps;': '\u2293\ufe00',
        'sqcup;': '\u2294',
        'sqcups;': '\u2294\ufe00',
        'Sqrt;': '\u221a',
        'sqsub;': '\u228f',
        'sqsube;': '\u2291',
        'sqsubset;': '\u228f',
        'sqsubseteq;': '\u2291',
        'sqsup;': '\u2290',
        'sqsupe;': '\u2292',
        'sqsupset;': '\u2290',
        'sqsupseteq;': '\u2292',
        'squ;': '\u25a1',
        'Square;': '\u25a1',
        'square;': '\u25a1',
        'SquareIntersection;': '\u2293',
        'SquareSubset;': '\u228f',
        'SquareSubsetEqual;': '\u2291',
        'SquareSuperset;': '\u2290',
        'SquareSupersetEqual;': '\u2292',
        'SquareUnion;': '\u2294',
        'squarf;': '\u25aa',
        'squf;': '\u25aa',
        'srarr;': '\u2192',
        'Sscr;': '\U0001d4ae',
        'sscr;': '\U0001d4c8',
        'ssetmn;': '\u2216',
        'ssmile;': '\u2323',
        'sstarf;': '\u22c6',
        'Star;': '\u22c6',
        'star;': '\u2606',
        'starf;': '\u2605',
        'straightepsilon;': '\u03f5',
        'straightphi;': '\u03d5',
        'strns;': '\xaf',
        'Sub;': '\u22d0',
        'sub;': '\u2282',
        'subdot;': '\u2abd',
        'subE;': '\u2ac5',
        'sube;': '\u2286',
        'subedot;': '\u2ac3',
        'submult;': '\u2ac1',
        'subnE;': '\u2acb',
        'subne;': '\u228a',
        'subplus;': '\u2abf',
        'subrarr;': '\u2979',
        'Subset;': '\u22d0',
        'subset;': '\u2282',
        'subseteq;': '\u2286',
        'subseteqq;': '\u2ac5',
        'SubsetEqual;': '\u2286',
        'subsetneq;': '\u228a',
        'subsetneqq;': '\u2acb',
        'subsim;': '\u2ac7',
        'subsub;': '\u2ad5',
        'subsup;': '\u2ad3',
        'succ;': '\u227b',
        'succapprox;': '\u2ab8',
        'succcurlyeq;': '\u227d',
        'Succeeds;': '\u227b',
        'SucceedsEqual;': '\u2ab0',
        'SucceedsSlantEqual;': '\u227d',
        'SucceedsTilde;': '\u227f',
        'succeq;': '\u2ab0',
        'succnapprox;': '\u2aba',
        'succneqq;': '\u2ab6',
        'succnsim;': '\u22e9',
        'succsim;': '\u227f',
        'SuchThat;': '\u220b',
        'Sum;': '\u2211',
        'sum;': '\u2211',
        'sung;': '\u266a',
        'sup1': '\xb9',
        'sup1;': '\xb9',
        'sup2': '\xb2',
        'sup2;': '\xb2',
        'sup3': '\xb3',
        'sup3;': '\xb3',
        'Sup;': '\u22d1',
        'sup;': '\u2283',
        'supdot;': '\u2abe',
        'supdsub;': '\u2ad8',
        'supE;': '\u2ac6',
        'supe;': '\u2287',
        'supedot;': '\u2ac4',
        'Superset;': '\u2283',
        'SupersetEqual;': '\u2287',
        'suphsol;': '\u27c9',
        'suphsub;': '\u2ad7',
        'suplarr;': '\u297b',
        'supmult;': '\u2ac2',
        'supnE;': '\u2acc',
        'supne;': '\u228b',
        'supplus;': '\u2ac0',
        'Supset;': '\u22d1',
        'supset;': '\u2283',
        'supseteq;': '\u2287',
        'supseteqq;': '\u2ac6',
        'supsetneq;': '\u228b',
        'supsetneqq;': '\u2acc',
        'supsim;': '\u2ac8',
        'supsub;': '\u2ad4',
        'supsup;': '\u2ad6',
        'swarhk;': '\u2926',
        'swArr;': '\u21d9',
        'swarr;': '\u2199',
        'swarrow;': '\u2199',
        'swnwar;': '\u292a',
        'szlig': '\xdf',
        'szlig;': '\xdf',
        'Tab;': '\t',
        'target;': '\u2316',
        'Tau;': '\u03a4',
        'tau;': '\u03c4',
        'tbrk;': '\u23b4',
        'Tcaron;': '\u0164',
        'tcaron;': '\u0165',
        'Tcedil;': '\u0162',
        'tcedil;': '\u0163',
        'Tcy;': '\u0422',
        'tcy;': '\u0442',
        'tdot;': '\u20db',
        'telrec;': '\u2315',
        'Tfr;': '\U0001d517',
        'tfr;': '\U0001d531',
        'there4;': '\u2234',
        'Therefore;': '\u2234',
        'therefore;': '\u2234',
        'Theta;': '\u0398',
        'theta;': '\u03b8',
        'thetasym;': '\u03d1',
        'thetav;': '\u03d1',
        'thickapprox;': '\u2248',
        'thicksim;': '\u223c',
        'ThickSpace;': '\u205f\u200a',
        'thinsp;': '\u2009',
        'ThinSpace;': '\u2009',
        'thkap;': '\u2248',
        'thksim;': '\u223c',
        'THORN': '\xde',
        'thorn': '\xfe',
        'THORN;': '\xde',
        'thorn;': '\xfe',
        'Tilde;': '\u223c',
        'tilde;': '\u02dc',
        'TildeEqual;': '\u2243',
        'TildeFullEqual;': '\u2245',
        'TildeTilde;': '\u2248',
        'times': '\xd7',
        'times;': '\xd7',
        'timesb;': '\u22a0',
        'timesbar;': '\u2a31',
        'timesd;': '\u2a30',
        'tint;': '\u222d',
        'toea;': '\u2928',
        'top;': '\u22a4',
        'topbot;': '\u2336',
        'topcir;': '\u2af1',
        'Topf;': '\U0001d54b',
        'topf;': '\U0001d565',
        'topfork;': '\u2ada',
        'tosa;': '\u2929',
        'tprime;': '\u2034',
        'TRADE;': '\u2122',
        'trade;': '\u2122',
        'triangle;': '\u25b5',
        'triangledown;': '\u25bf',
        'triangleleft;': '\u25c3',
        'trianglelefteq;': '\u22b4',
        'triangleq;': '\u225c',
        'triangleright;': '\u25b9',
        'trianglerighteq;': '\u22b5',
        'tridot;': '\u25ec',
        'trie;': '\u225c',
        'triminus;': '\u2a3a',
        'TripleDot;': '\u20db',
        'triplus;': '\u2a39',
        'trisb;': '\u29cd',
        'tritime;': '\u2a3b',
        'trpezium;': '\u23e2',
        'Tscr;': '\U0001d4af',
        'tscr;': '\U0001d4c9',
        'TScy;': '\u0426',
        'tscy;': '\u0446',
        'TSHcy;': '\u040b',
        'tshcy;': '\u045b',
        'Tstrok;': '\u0166',
        'tstrok;': '\u0167',
        'twixt;': '\u226c',
        'twoheadleftarrow;': '\u219e',
        'twoheadrightarrow;': '\u21a0',
        'Uacute': '\xda',
        'uacute': '\xfa',
        'Uacute;': '\xda',
        'uacute;': '\xfa',
        'Uarr;': '\u219f',
        'uArr;': '\u21d1',
        'uarr;': '\u2191',
        'Uarrocir;': '\u2949',
        'Ubrcy;': '\u040e',
        'ubrcy;': '\u045e',
        'Ubreve;': '\u016c',
        'ubreve;': '\u016d',
        'Ucirc': '\xdb',
        'ucirc': '\xfb',
        'Ucirc;': '\xdb',
        'ucirc;': '\xfb',
        'Ucy;': '\u0423',
        'ucy;': '\u0443',
        'udarr;': '\u21c5',
        'Udblac;': '\u0170',
        'udblac;': '\u0171',
        'udhar;': '\u296e',
        'ufisht;': '\u297e',
        'Ufr;': '\U0001d518',
        'ufr;': '\U0001d532',
        'Ugrave': '\xd9',
        'ugrave': '\xf9',
        'Ugrave;': '\xd9',
        'ugrave;': '\xf9',
        'uHar;': '\u2963',
        'uharl;': '\u21bf',
        'uharr;': '\u21be',
        'uhblk;': '\u2580',
        'ulcorn;': '\u231c',
        'ulcorner;': '\u231c',
        'ulcrop;': '\u230f',
        'ultri;': '\u25f8',
        'Umacr;': '\u016a',
        'umacr;': '\u016b',
        'uml': '\xa8',
        'uml;': '\xa8',
        'UnderBar;': '_',
        'UnderBrace;': '\u23df',
        'UnderBracket;': '\u23b5',
        'UnderParenthesis;': '\u23dd',
        'Union;': '\u22c3',
        'UnionPlus;': '\u228e',
        'Uogon;': '\u0172',
        'uogon;': '\u0173',
        'Uopf;': '\U0001d54c',
        'uopf;': '\U0001d566',
        'UpArrow;': '\u2191',
        'Uparrow;': '\u21d1',
        'uparrow;': '\u2191',
        'UpArrowBar;': '\u2912',
        'UpArrowDownArrow;': '\u21c5',
        'UpDownArrow;': '\u2195',
        'Updownarrow;': '\u21d5',
        'updownarrow;': '\u2195',
        'UpEquilibrium;': '\u296e',
        'upharpoonleft;': '\u21bf',
        'upharpoonright;': '\u21be',
        'uplus;': '\u228e',
        'UpperLeftArrow;': '\u2196',
        'UpperRightArrow;': '\u2197',
        'Upsi;': '\u03d2',
        'upsi;': '\u03c5',
        'upsih;': '\u03d2',
        'Upsilon;': '\u03a5',
        'upsilon;': '\u03c5',
        'UpTee;': '\u22a5',
        'UpTeeArrow;': '\u21a5',
        'upuparrows;': '\u21c8',
        'urcorn;': '\u231d',
        'urcorner;': '\u231d',
        'urcrop;': '\u230e',
        'Uring;': '\u016e',
        'uring;': '\u016f',
        'urtri;': '\u25f9',
        'Uscr;': '\U0001d4b0',
        'uscr;': '\U0001d4ca',
        'utdot;': '\u22f0',
        'Utilde;': '\u0168',
        'utilde;': '\u0169',
        'utri;': '\u25b5',
        'utrif;': '\u25b4',
        'uuarr;': '\u21c8',
        'Uuml': '\xdc',
        'uuml': '\xfc',
        'Uuml;': '\xdc',
        'uuml;': '\xfc',
        'uwangle;': '\u29a7',
        'vangrt;': '\u299c',
        'varepsilon;': '\u03f5',
        'varkappa;': '\u03f0',
        'varnothing;': '\u2205',
        'varphi;': '\u03d5',
        'varpi;': '\u03d6',
        'varpropto;': '\u221d',
        'vArr;': '\u21d5',
        'varr;': '\u2195',
        'varrho;': '\u03f1',
        'varsigma;': '\u03c2',
        'varsubsetneq;': '\u228a\ufe00',
        'varsubsetneqq;': '\u2acb\ufe00',
        'varsupsetneq;': '\u228b\ufe00',
        'varsupsetneqq;': '\u2acc\ufe00',
        'vartheta;': '\u03d1',
        'vartriangleleft;': '\u22b2',
        'vartriangleright;': '\u22b3',
        'Vbar;': '\u2aeb',
        'vBar;': '\u2ae8',
        'vBarv;': '\u2ae9',
        'Vcy;': '\u0412',
        'vcy;': '\u0432',
        'VDash;': '\u22ab',
        'Vdash;': '\u22a9',
        'vDash;': '\u22a8',
        'vdash;': '\u22a2',
        'Vdashl;': '\u2ae6',
        'Vee;': '\u22c1',
        'vee;': '\u2228',
        'veebar;': '\u22bb',
        'veeeq;': '\u225a',
        'vellip;': '\u22ee',
        'Verbar;': '\u2016',
        'verbar;': '|',
        'Vert;': '\u2016',
        'vert;': '|',
        'VerticalBar;': '\u2223',
        'VerticalLine;': '|',
        'VerticalSeparator;': '\u2758',
        'VerticalTilde;': '\u2240',
        'VeryThinSpace;': '\u200a',
        'Vfr;': '\U0001d519',
        'vfr;': '\U0001d533',
        'vltri;': '\u22b2',
        'vnsub;': '\u2282\u20d2',
        'vnsup;': '\u2283\u20d2',
        'Vopf;': '\U0001d54d',
        'vopf;': '\U0001d567',
        'vprop;': '\u221d',
        'vrtri;': '\u22b3',
        'Vscr;': '\U0001d4b1',
        'vscr;': '\U0001d4cb',
        'vsubnE;': '\u2acb\ufe00',
        'vsubne;': '\u228a\ufe00',
        'vsupnE;': '\u2acc\ufe00',
        'vsupne;': '\u228b\ufe00',
        'Vvdash;': '\u22aa',
        'vzigzag;': '\u299a',
        'Wcirc;': '\u0174',
        'wcirc;': '\u0175',
        'wedbar;': '\u2a5f',
        'Wedge;': '\u22c0',
        'wedge;': '\u2227',
        'wedgeq;': '\u2259',
        'weierp;': '\u2118',
        'Wfr;': '\U0001d51a',
        'wfr;': '\U0001d534',
        'Wopf;': '\U0001d54e',
        'wopf;': '\U0001d568',
        'wp;': '\u2118',
        'wr;': '\u2240',
        'wreath;': '\u2240',
        'Wscr;': '\U0001d4b2',
        'wscr;': '\U0001d4cc',
        'xcap;': '\u22c2',
        'xcirc;': '\u25ef',
        'xcup;': '\u22c3',
        'xdtri;': '\u25bd',
        'Xfr;': '\U0001d51b',
        'xfr;': '\U0001d535',
        'xhArr;': '\u27fa',
        'xharr;': '\u27f7',
        'Xi;': '\u039e',
        'xi;': '\u03be',
        'xlArr;': '\u27f8',
        'xlarr;': '\u27f5',
        'xmap;': '\u27fc',
        'xnis;': '\u22fb',
        'xodot;': '\u2a00',
        'Xopf;': '\U0001d54f',
        'xopf;': '\U0001d569',
        'xoplus;': '\u2a01',
        'xotime;': '\u2a02',
        'xrArr;': '\u27f9',
        'xrarr;': '\u27f6',
        'Xscr;': '\U0001d4b3',
        'xscr;': '\U0001d4cd',
        'xsqcup;': '\u2a06',
        'xuplus;': '\u2a04',
        'xutri;': '\u25b3',
        'xvee;': '\u22c1',
        'xwedge;': '\u22c0',
        'Yacute': '\xdd',
        'yacute': '\xfd',
        'Yacute;': '\xdd',
        'yacute;': '\xfd',
        'YAcy;': '\u042f',
        'yacy;': '\u044f',
        'Ycirc;': '\u0176',
        'ycirc;': '\u0177',
        'Ycy;': '\u042b',
        'ycy;': '\u044b',
        'yen': '\xa5',
        'yen;': '\xa5',
        'Yfr;': '\U0001d51c',
        'yfr;': '\U0001d536',
        'YIcy;': '\u0407',
        'yicy;': '\u0457',
        'Yopf;': '\U0001d550',
        'yopf;': '\U0001d56a',
        'Yscr;': '\U0001d4b4',
        'yscr;': '\U0001d4ce',
        'YUcy;': '\u042e',
        'yucy;': '\u044e',
        'yuml': '\xff',
        'Yuml;': '\u0178',
        'yuml;': '\xff',
        'Zacute;': '\u0179',
        'zacute;': '\u017a',
        'Zcaron;': '\u017d',
        'zcaron;': '\u017e',
        'Zcy;': '\u0417',
        'zcy;': '\u0437',
        'Zdot;': '\u017b',
        'zdot;': '\u017c',
        'zeetrf;': '\u2128',
        'ZeroWidthSpace;': '\u200b',
        'Zeta;': '\u0396',
        'zeta;': '\u03b6',
        'Zfr;': '\u2128',
        'zfr;': '\U0001d537',
        'ZHcy;': '\u0416',
        'zhcy;': '\u0436',
        'zigrarr;': '\u21dd',
        'Zopf;': '\u2124',
        'zopf;': '\U0001d56b',
        'Zscr;': '\U0001d4b5',
        'zscr;': '\U0001d4cf',
        'zwj;': '\u200d',
        'zwnj;': '\u200c',
    }

try:
    import http.client as compat_http_client
except ImportError:  # Python 2
    import httplib as compat_http_client

try:
    from urllib.error import HTTPError as compat_HTTPError
except ImportError:  # Python 2
    from urllib2 import HTTPError as compat_HTTPError

try:
    from urllib.request import urlretrieve as compat_urlretrieve
except ImportError:  # Python 2
    from urllib import urlretrieve as compat_urlretrieve

try:
    from html.parser import HTMLParser as compat_HTMLParser
except ImportError:  # Python 2
    from HTMLParser import HTMLParser as compat_HTMLParser

try:  # Python 2
    from HTMLParser import HTMLParseError as compat_HTMLParseError
except ImportError:  # Python <3.4
    try:
        from html.parser import HTMLParseError as compat_HTMLParseError
    except ImportError:  # Python >3.4

        # HTMLParseError has been deprecated in Python 3.3 and removed in
        # Python 3.5. Introducing dummy exception for Python >3.5 for compatible
        # and uniform cross-version exception handling
        class compat_HTMLParseError(Exception):
            pass

try:
    from subprocess import DEVNULL
    compat_subprocess_get_DEVNULL = lambda: DEVNULL
except ImportError:
    compat_subprocess_get_DEVNULL = lambda: open(os.path.devnull, 'w')

try:
    import http.server as compat_http_server
except ImportError:
    import BaseHTTPServer as compat_http_server

try:
    compat_str = unicode  # Python 2
except NameError:
    compat_str = str

try:
    from urllib.parse import quote as compat_urllib_parse_quote
    from urllib.parse import quote_plus as compat_urllib_parse_quote_plus
except ImportError:  # Python 2
    def compat_urllib_parse_quote(string, safe='/'):
        return compat_urllib_parse.quote(
            string.encode('utf-8'),
            str(safe))

    def compat_urllib_parse_quote_plus(string, safe=''):
        return compat_urllib_parse.quote_plus(
            string.encode('utf-8'),
            str(safe))

try:
    from urllib.parse import unquote_to_bytes as compat_urllib_parse_unquote_to_bytes
    from urllib.parse import unquote as compat_urllib_parse_unquote
    from urllib.parse import unquote_plus as compat_urllib_parse_unquote_plus
except ImportError:  # Python 2
    _asciire = (compat_urllib_parse._asciire if hasattr(compat_urllib_parse, '_asciire')
                else re.compile(r'([\x00-\x7f]+)'))

    # HACK: The following are the correct unquote_to_bytes, unquote and unquote_plus
    # implementations from cpython 3.4.3's stdlib. Python 2's version
    # is apparently broken (see https://github.com/ytdl-org/youtube-dl/pull/6244)

    def compat_urllib_parse_unquote_to_bytes(string):
        """unquote_to_bytes('abc%20def') -> b'abc def'."""
        # Note: strings are encoded as UTF-8. This is only an issue if it contains
        # unescaped non-ASCII characters, which URIs should not.
        if not string:
            # Is it a string-like object?
            string.split
            return b''
        if isinstance(string, compat_str):
            string = string.encode('utf-8')
        bits = string.split(b'%')
        if len(bits) == 1:
            return string
        res = [bits[0]]
        append = res.append
        for item in bits[1:]:
            try:
                append(compat_urllib_parse._hextochr[item[:2]])
                append(item[2:])
            except KeyError:
                append(b'%')
                append(item)
        return b''.join(res)

    def compat_urllib_parse_unquote(string, encoding='utf-8', errors='replace'):
        """Replace %xx escapes by their single-character equivalent. The optional
        encoding and errors parameters specify how to decode percent-encoded
        sequences into Unicode characters, as accepted by the bytes.decode()
        method.
        By default, percent-encoded sequences are decoded with UTF-8, and invalid
        sequences are replaced by a placeholder character.

        unquote('abc%20def') -> 'abc def'.
        """
        if '%' not in string:
            string.split
            return string
        if encoding is None:
            encoding = 'utf-8'
        if errors is None:
            errors = 'replace'
        bits = _asciire.split(string)
        res = [bits[0]]
        append = res.append
        for i in range(1, len(bits), 2):
            append(compat_urllib_parse_unquote_to_bytes(bits[i]).decode(encoding, errors))
            append(bits[i + 1])
        return ''.join(res)

    def compat_urllib_parse_unquote_plus(string, encoding='utf-8', errors='replace'):
        """Like unquote(), but also replace plus signs by spaces, as required for
        unquoting HTML form values.

        unquote_plus('%7e/abc+def') -> '~/abc def'
        """
        string = string.replace('+', ' ')
        return compat_urllib_parse_unquote(string, encoding, errors)

try:
    from urllib.parse import urlencode as compat_urllib_parse_urlencode
except ImportError:  # Python 2
    # Python 2 will choke in urlencode on mixture of byte and unicode strings.
    # Possible solutions are to either port it from python 3 with all
    # the friends or manually ensure input query contains only byte strings.
    # We will stick with latter thus recursively encoding the whole query.
    def compat_urllib_parse_urlencode(query, doseq=0, encoding='utf-8'):
        def encode_elem(e):
            if isinstance(e, dict):
                e = encode_dict(e)
            elif isinstance(e, (list, tuple,)):
                list_e = encode_list(e)
                e = tuple(list_e) if isinstance(e, tuple) else list_e
            elif isinstance(e, compat_str):
                e = e.encode(encoding)
            return e

        def encode_dict(d):
            return dict((encode_elem(k), encode_elem(v)) for k, v in d.items())

        def encode_list(l):
            return [encode_elem(e) for e in l]

        return compat_urllib_parse.urlencode(encode_elem(query), doseq=doseq)

try:
    from urllib.request import DataHandler as compat_urllib_request_DataHandler
except ImportError:  # Python < 3.4
    # Ported from CPython 98774:1733b3bd46db, Lib/urllib/request.py
    class compat_urllib_request_DataHandler(compat_urllib_request.BaseHandler):
        def data_open(self, req):
            # data URLs as specified in RFC 2397.
            #
            # ignores POSTed data
            #
            # syntax:
            # dataurl   := "data:" [ mediatype ] [ ";base64" ] "," data
            # mediatype := [ type "/" subtype ] *( ";" parameter )
            # data      := *urlchar
            # parameter := attribute "=" value
            url = req.get_full_url()

            scheme, data = url.split(':', 1)
            mediatype, data = data.split(',', 1)

            # even base64 encoded data URLs might be quoted so unquote in any case:
            data = compat_urllib_parse_unquote_to_bytes(data)
            if mediatype.endswith(';base64'):
                data = binascii.a2b_base64(data)
                mediatype = mediatype[:-7]

            if not mediatype:
                mediatype = 'text/plain;charset=US-ASCII'

            headers = email.message_from_string(
                'Content-type: %s\nContent-length: %d\n' % (mediatype, len(data)))

            return compat_urllib_response.addinfourl(io.BytesIO(data), headers, url)

try:
    compat_basestring = basestring  # Python 2
except NameError:
    compat_basestring = str

try:
    compat_chr = unichr  # Python 2
except NameError:
    compat_chr = chr

try:
    from xml.etree.ElementTree import ParseError as compat_xml_parse_error
except ImportError:  # Python 2.6
    from xml.parsers.expat import ExpatError as compat_xml_parse_error


etree = xml.etree.ElementTree


class _TreeBuilder(etree.TreeBuilder):
    def doctype(self, name, pubid, system):
        pass


try:
    # xml.etree.ElementTree.Element is a method in Python <=2.6 and
    # the following will crash with:
    #  TypeError: isinstance() arg 2 must be a class, type, or tuple of classes and types
    isinstance(None, xml.etree.ElementTree.Element)
    from xml.etree.ElementTree import Element as compat_etree_Element
except TypeError:  # Python <=2.6
    from xml.etree.ElementTree import _ElementInterface as compat_etree_Element

if sys.version_info[0] >= 3:
    def compat_etree_fromstring(text):
        return etree.XML(text, parser=etree.XMLParser(target=_TreeBuilder()))
else:
    # python 2.x tries to encode unicode strings with ascii (see the
    # XMLParser._fixtext method)
    try:
        _etree_iter = etree.Element.iter
    except AttributeError:  # Python <=2.6
        def _etree_iter(root):
            for el in root.findall('*'):
                yield el
                for sub in _etree_iter(el):
                    yield sub

    # on 2.6 XML doesn't have a parser argument, function copied from CPython
    # 2.7 source
    def _XML(text, parser=None):
        if not parser:
            parser = etree.XMLParser(target=_TreeBuilder())
        parser.feed(text)
        return parser.close()

    def _element_factory(*args, **kwargs):
        el = etree.Element(*args, **kwargs)
        for k, v in el.items():
            if isinstance(v, bytes):
                el.set(k, v.decode('utf-8'))
        return el

    def compat_etree_fromstring(text):
        doc = _XML(text, parser=etree.XMLParser(target=_TreeBuilder(element_factory=_element_factory)))
        for el in _etree_iter(doc):
            if el.text is not None and isinstance(el.text, bytes):
                el.text = el.text.decode('utf-8')
        return doc

if hasattr(etree, 'register_namespace'):
    compat_etree_register_namespace = etree.register_namespace
else:
    def compat_etree_register_namespace(prefix, uri):
        """Register a namespace prefix.
        The registry is global, and any existing mapping for either the
        given prefix or the namespace URI will be removed.
        *prefix* is the namespace prefix, *uri* is a namespace uri. Tags and
        attributes in this namespace will be serialized with prefix if possible.
        ValueError is raised if prefix is reserved or is invalid.
        """
        if re.match(r"ns\d+$", prefix):
            raise ValueError("Prefix format reserved for internal use")
        for k, v in list(etree._namespace_map.items()):
            if k == uri or v == prefix:
                del etree._namespace_map[k]
        etree._namespace_map[uri] = prefix

if sys.version_info < (2, 7):
    # Here comes the crazy part: In 2.6, if the xpath is a unicode,
    # .//node does not match if a node is a direct child of . !
    def compat_xpath(xpath):
        if isinstance(xpath, compat_str):
            xpath = xpath.encode('ascii')
        return xpath
else:
    compat_xpath = lambda xpath: xpath

try:
    from urllib.parse import parse_qs as compat_parse_qs
except ImportError:  # Python 2
    # HACK: The following is the correct parse_qs implementation from cpython 3's stdlib.
    # Python 2's version is apparently totally broken

    def _parse_qsl(qs, keep_blank_values=False, strict_parsing=False,
                   encoding='utf-8', errors='replace'):
        qs, _coerce_result = qs, compat_str
        pairs = [s2 for s1 in qs.split('&') for s2 in s1.split(';')]
        r = []
        for name_value in pairs:
            if not name_value and not strict_parsing:
                continue
            nv = name_value.split('=', 1)
            if len(nv) != 2:
                if strict_parsing:
                    raise ValueError('bad query field: %r' % (name_value,))
                # Handle case of a control-name with no equal sign
                if keep_blank_values:
                    nv.append('')
                else:
                    continue
            if len(nv[1]) or keep_blank_values:
                name = nv[0].replace('+', ' ')
                name = compat_urllib_parse_unquote(
                    name, encoding=encoding, errors=errors)
                name = _coerce_result(name)
                value = nv[1].replace('+', ' ')
                value = compat_urllib_parse_unquote(
                    value, encoding=encoding, errors=errors)
                value = _coerce_result(value)
                r.append((name, value))
        return r

    def compat_parse_qs(qs, keep_blank_values=False, strict_parsing=False,
                        encoding='utf-8', errors='replace'):
        parsed_result = {}
        pairs = _parse_qsl(qs, keep_blank_values, strict_parsing,
                           encoding=encoding, errors=errors)
        for name, value in pairs:
            if name in parsed_result:
                parsed_result[name].append(value)
            else:
                parsed_result[name] = [value]
        return parsed_result


compat_os_name = os._name if os.name == 'java' else os.name


if compat_os_name == 'nt':
    def compat_shlex_quote(s):
        return s if re.match(r'^[-_\w./]+$', s) else '"%s"' % s.replace('"', '\\"')
else:
    try:
        from shlex import quote as compat_shlex_quote
    except ImportError:  # Python < 3.3
        def compat_shlex_quote(s):
            if re.match(r'^[-_\w./]+$', s):
                return s
            else:
                return "'" + s.replace("'", "'\"'\"'") + "'"


try:
    args = shlex.split('中文')
    assert (isinstance(args, list)
            and isinstance(args[0], compat_str)
            and args[0] == '中文')
    compat_shlex_split = shlex.split
except (AssertionError, UnicodeEncodeError):
    # Working around shlex issue with unicode strings on some python 2
    # versions (see http://bugs.python.org/issue1548891)
    def compat_shlex_split(s, comments=False, posix=True):
        if isinstance(s, compat_str):
            s = s.encode('utf-8')
        return list(map(lambda s: s.decode('utf-8'), shlex.split(s, comments, posix)))


def compat_ord(c):
    if type(c) is int:
        return c
    else:
        return ord(c)


if sys.version_info >= (3, 0):
    compat_getenv = os.getenv
    compat_expanduser = os.path.expanduser

    def compat_setenv(key, value, env=os.environ):
        env[key] = value
else:
    # Environment variables should be decoded with filesystem encoding.
    # Otherwise it will fail if any non-ASCII characters present (see #3854 #3217 #2918)

    def compat_getenv(key, default=None):
        from .utils import get_filesystem_encoding
        env = os.getenv(key, default)
        if env:
            env = env.decode(get_filesystem_encoding())
        return env

    def compat_setenv(key, value, env=os.environ):
        def encode(v):
            from .utils import get_filesystem_encoding
            return v.encode(get_filesystem_encoding()) if isinstance(v, compat_str) else v
        env[encode(key)] = encode(value)

    # HACK: The default implementations of os.path.expanduser from cpython do not decode
    # environment variables with filesystem encoding. We will work around this by
    # providing adjusted implementations.
    # The following are os.path.expanduser implementations from cpython 2.7.8 stdlib
    # for different platforms with correct environment variables decoding.

    if compat_os_name == 'posix':
        def compat_expanduser(path):
            """Expand ~ and ~user constructions.  If user or $HOME is unknown,
            do nothing."""
            if not path.startswith('~'):
                return path
            i = path.find('/', 1)
            if i < 0:
                i = len(path)
            if i == 1:
                if 'HOME' not in os.environ:
                    import pwd
                    userhome = pwd.getpwuid(os.getuid()).pw_dir
                else:
                    userhome = compat_getenv('HOME')
            else:
                import pwd
                try:
                    pwent = pwd.getpwnam(path[1:i])
                except KeyError:
                    return path
                userhome = pwent.pw_dir
            userhome = userhome.rstrip('/')
            return (userhome + path[i:]) or '/'
    elif compat_os_name in ('nt', 'ce'):
        def compat_expanduser(path):
            """Expand ~ and ~user constructs.

            If user or $HOME is unknown, do nothing."""
            if path[:1] != '~':
                return path
            i, n = 1, len(path)
            while i < n and path[i] not in '/\\':
                i = i + 1

            if 'HOME' in os.environ:
                userhome = compat_getenv('HOME')
            elif 'USERPROFILE' in os.environ:
                userhome = compat_getenv('USERPROFILE')
            elif 'HOMEPATH' not in os.environ:
                return path
            else:
                try:
                    drive = compat_getenv('HOMEDRIVE')
                except KeyError:
                    drive = ''
                userhome = os.path.join(drive, compat_getenv('HOMEPATH'))

            if i != 1:  # ~user
                userhome = os.path.join(os.path.dirname(userhome), path[1:i])

            return userhome + path[i:]
    else:
        compat_expanduser = os.path.expanduser


if compat_os_name == 'nt' and sys.version_info < (3, 8):
    # os.path.realpath on Windows does not follow symbolic links
    # prior to Python 3.8 (see https://bugs.python.org/issue9949)
    def compat_realpath(path):
        while os.path.islink(path):
            path = os.path.abspath(os.readlink(path))
        return path
else:
    compat_realpath = os.path.realpath


if sys.version_info < (3, 0):
    def compat_print(s):
        from .utils import preferredencoding
        print(s.encode(preferredencoding(), 'xmlcharrefreplace'))
else:
    def compat_print(s):
        assert isinstance(s, compat_str)
        print(s)


if sys.version_info < (3, 0) and sys.platform == 'win32':
    def compat_getpass(prompt, *args, **kwargs):
        if isinstance(prompt, compat_str):
            from .utils import preferredencoding
            prompt = prompt.encode(preferredencoding())
        return getpass.getpass(prompt, *args, **kwargs)
else:
    compat_getpass = getpass.getpass

try:
    compat_input = raw_input
except NameError:  # Python 3
    compat_input = input

# Python < 2.6.5 require kwargs to be bytes
try:
    def _testfunc(x):
        pass
    _testfunc(**{'x': 0})
except TypeError:
    def compat_kwargs(kwargs):
        return dict((bytes(k), v) for k, v in kwargs.items())
else:
    compat_kwargs = lambda kwargs: kwargs


try:
    compat_numeric_types = (int, float, long, complex)
except NameError:  # Python 3
    compat_numeric_types = (int, float, complex)


try:
    compat_integer_types = (int, long)
except NameError:  # Python 3
    compat_integer_types = (int, )


if sys.version_info < (2, 7):
    def compat_socket_create_connection(address, timeout, source_address=None):
        host, port = address
        err = None
        for res in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            sock = None
            try:
                sock = socket.socket(af, socktype, proto)
                sock.settimeout(timeout)
                if source_address:
                    sock.bind(source_address)
                sock.connect(sa)
                return sock
            except socket.error as _:
                err = _
                if sock is not None:
                    sock.close()
        if err is not None:
            raise err
        else:
            raise socket.error('getaddrinfo returns an empty list')
else:
    compat_socket_create_connection = socket.create_connection


# Fix https://github.com/ytdl-org/youtube-dl/issues/4223
# See http://bugs.python.org/issue9161 for what is broken
def workaround_optparse_bug9161():
    op = optparse.OptionParser()
    og = optparse.OptionGroup(op, 'foo')
    try:
        og.add_option('-t')
    except TypeError:
        real_add_option = optparse.OptionGroup.add_option

        def _compat_add_option(self, *args, **kwargs):
            enc = lambda v: (
                v.encode('ascii', 'replace') if isinstance(v, compat_str)
                else v)
            bargs = [enc(a) for a in args]
            bkwargs = dict(
                (k, enc(v)) for k, v in kwargs.items())
            return real_add_option(self, *bargs, **bkwargs)
        optparse.OptionGroup.add_option = _compat_add_option


if hasattr(shutil, 'get_terminal_size'):  # Python >= 3.3
    compat_get_terminal_size = shutil.get_terminal_size
else:
    _terminal_size = collections.namedtuple('terminal_size', ['columns', 'lines'])

    def compat_get_terminal_size(fallback=(80, 24)):
        from .utils import process_communicate_or_kill
        columns = compat_getenv('COLUMNS')
        if columns:
            columns = int(columns)
        else:
            columns = None
        lines = compat_getenv('LINES')
        if lines:
            lines = int(lines)
        else:
            lines = None

        if columns is None or lines is None or columns <= 0 or lines <= 0:
            try:
                sp = subprocess.Popen(
                    ['stty', 'size'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err = process_communicate_or_kill(sp)
                _lines, _columns = map(int, out.split())
            except Exception:
                _columns, _lines = _terminal_size(*fallback)

            if columns is None or columns <= 0:
                columns = _columns
            if lines is None or lines <= 0:
                lines = _lines
        return _terminal_size(columns, lines)

try:
    itertools.count(start=0, step=1)
    compat_itertools_count = itertools.count
except TypeError:  # Python 2.6
    def compat_itertools_count(start=0, step=1):
        n = start
        while True:
            yield n
            n += step

if sys.version_info >= (3, 0):
    from tokenize import tokenize as compat_tokenize_tokenize
else:
    from tokenize import generate_tokens as compat_tokenize_tokenize


try:
    struct.pack('!I', 0)
except TypeError:
    # In Python 2.6 and 2.7.x < 2.7.7, struct requires a bytes argument
    # See https://bugs.python.org/issue19099
    def compat_struct_pack(spec, *args):
        if isinstance(spec, compat_str):
            spec = spec.encode('ascii')
        return struct.pack(spec, *args)

    def compat_struct_unpack(spec, *args):
        if isinstance(spec, compat_str):
            spec = spec.encode('ascii')
        return struct.unpack(spec, *args)

    class compat_Struct(struct.Struct):
        def __init__(self, fmt):
            if isinstance(fmt, compat_str):
                fmt = fmt.encode('ascii')
            super(compat_Struct, self).__init__(fmt)
else:
    compat_struct_pack = struct.pack
    compat_struct_unpack = struct.unpack
    if platform.python_implementation() == 'IronPython' and sys.version_info < (2, 7, 8):
        class compat_Struct(struct.Struct):
            def unpack(self, string):
                if not isinstance(string, buffer):  # noqa: F821
                    string = buffer(string)  # noqa: F821
                return super(compat_Struct, self).unpack(string)
    else:
        compat_Struct = struct.Struct


try:
    from future_builtins import zip as compat_zip
except ImportError:  # not 2.6+ or is 3.x
    try:
        from itertools import izip as compat_zip  # < 2.5 or 3.x
    except ImportError:
        compat_zip = zip


if sys.version_info < (3, 3):
    def compat_b64decode(s, *args, **kwargs):
        if isinstance(s, compat_str):
            s = s.encode('ascii')
        return base64.b64decode(s, *args, **kwargs)
else:
    compat_b64decode = base64.b64decode


if platform.python_implementation() == 'PyPy' and sys.pypy_version_info < (5, 4, 0):
    # PyPy2 prior to version 5.4.0 expects byte strings as Windows function
    # names, see the original PyPy issue [1] and the yt-dlp one [2].
    # 1. https://bitbucket.org/pypy/pypy/issues/2360/windows-ctypescdll-typeerror-function-name
    # 2. https://github.com/ytdl-org/youtube-dl/pull/4392
    def compat_ctypes_WINFUNCTYPE(*args, **kwargs):
        real = ctypes.WINFUNCTYPE(*args, **kwargs)

        def resf(tpl, *args, **kwargs):
            funcname, dll = tpl
            return real((str(funcname), dll), *args, **kwargs)

        return resf
else:
    def compat_ctypes_WINFUNCTYPE(*args, **kwargs):
        return ctypes.WINFUNCTYPE(*args, **kwargs)


__all__ = [
    'compat_HTMLParseError',
    'compat_HTMLParser',
    'compat_HTTPError',
    'compat_Struct',
    'compat_b64decode',
    'compat_basestring',
    'compat_chr',
    'compat_cookiejar',
    'compat_cookiejar_Cookie',
    'compat_cookies',
    'compat_cookies_SimpleCookie',
    'compat_ctypes_WINFUNCTYPE',
    'compat_etree_Element',
    'compat_etree_fromstring',
    'compat_etree_register_namespace',
    'compat_expanduser',
    'compat_get_terminal_size',
    'compat_getenv',
    'compat_getpass',
    'compat_html_entities',
    'compat_html_entities_html5',
    'compat_http_client',
    'compat_http_server',
    'compat_input',
    'compat_integer_types',
    'compat_itertools_count',
    'compat_kwargs',
    'compat_numeric_types',
    'compat_ord',
    'compat_os_name',
    'compat_parse_qs',
    'compat_print',
    'compat_realpath',
    'compat_setenv',
    'compat_shlex_quote',
    'compat_shlex_split',
    'compat_socket_create_connection',
    'compat_str',
    'compat_struct_pack',
    'compat_struct_unpack',
    'compat_subprocess_get_DEVNULL',
    'compat_tokenize_tokenize',
    'compat_urllib_error',
    'compat_urllib_parse',
    'compat_urllib_parse_quote',
    'compat_urllib_parse_quote_plus',
    'compat_urllib_parse_unquote',
    'compat_urllib_parse_unquote_plus',
    'compat_urllib_parse_unquote_to_bytes',
    'compat_urllib_parse_urlencode',
    'compat_urllib_parse_urlparse',
    'compat_urllib_parse_urlunparse',
    'compat_urllib_request',
    'compat_urllib_request_DataHandler',
    'compat_urllib_response',
    'compat_urlparse',
    'compat_urlretrieve',
    'compat_xml_parse_error',
    'compat_xpath',
    'compat_zip',
    'workaround_optparse_bug9161',
]
