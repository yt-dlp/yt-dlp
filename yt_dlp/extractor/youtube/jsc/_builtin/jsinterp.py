import json
import os
import re
import traceback
from collections.abc import Generator

from yt_dlp import join_nonempty, traverse_obj
from yt_dlp.extractor.youtube.jsc.provider import (
    JsChallengeProvider,
    JsChallengeProviderError,
    JsChallengeProviderResponse,
    JsChallengeRequest,
    JsChallengeResponse,
    JsChallengeType,
    NSigChallengeOutput,
    SigChallengeOutput,
    register_provider,
)
from yt_dlp.extractor.youtube.pot._provider import BuiltinIEContentProvider
from yt_dlp.jsinterp import JSInterpreter, LocalNameSpace
from yt_dlp.utils import ExtractorError, filter_dict, js_to_json, urljoin


@register_provider
class JsInterpJCP(JsChallengeProvider, BuiltinIEContentProvider):
    PROVIDER_NAME = 'jsinterp'
    _SUPPORTED_TYPES = [JsChallengeType.SIG, JsChallengeType.NSIG]

    _NSIG_FUNC_CACHE_ID = 'nsig func'
    _DUMMY_STRING = 'dlp_wins'

    def is_available(self) -> bool:
        return True

    def _real_bulk_solve(self, requests: list[JsChallengeRequest]) -> Generator[JsChallengeProviderResponse, None, None]:
        for request in requests:
            try:
                if request.type == JsChallengeType.SIG:
                    output = self._solve_sig_challenges(request)
                else:
                    output = self._solve_nsig_challenges(request)
                yield JsChallengeProviderResponse(
                    request=request, response=JsChallengeResponse(type=request.type, output=output))
            except Exception as e:
                yield JsChallengeProviderResponse(request=request, error=e)

    def _solve_sig_challenges(self, request: JsChallengeRequest) -> SigChallengeOutput:
        """Turn the s field into a working signature"""
        results = {}
        for challenge in request.input.challenges:
            extract_sig = self.ie._cached(
                self._extract_signature_function, 'sig', request.player_url, self._signature_cache_id(challenge))
            func = extract_sig(request.video_id, request.player_url, challenge)
            self._print_sig_code(func, challenge)
            results[challenge] = func(challenge)

        return SigChallengeOutput(results=results)

    def _solve_nsig_challenges(self, request: JsChallengeRequest) -> NSigChallengeOutput:
        """Turn the encrypted n field into a working signature"""
        results = {}
        for challenge in request.input.challenges:
            results[challenge] = self._solve_nsig_challenge(challenge, request.video_id, request.player_url)

        return NSigChallengeOutput(results=results)

    def _solve_nsig_challenge(self, challenge, video_id, player_url) -> str:
        """Turn the encrypted n field into a working signature"""
        if player_url is None:
            raise JsChallengeProviderError('Cannot decrypt nsig without player_url')

        # TODO: do this in IE
        player_url = urljoin('https://www.youtube.com', player_url)

        try:
            jsi, player_id, func_code = self._extract_n_function_code(video_id, player_url)
        except ExtractorError as e:
            raise JsChallengeProviderError(f'Unable to extract nsig function code: {e}') from e
        if self.ie.get_param('youtube_print_sig_code'):
            self.logger.info(f'Extracted nsig function from {player_id}:\n{func_code[1]}\n')

        try:
            extract_nsig = self.ie._cached(self._extract_n_function_from_code, self._NSIG_FUNC_CACHE_ID, player_url)
            ret = extract_nsig(jsi, func_code)(challenge)
        except JSInterpreter.Exception as e:
            self.logger.debug(str(e))  # TODO: only print once
            raise JsChallengeProviderError(
                f'Native nsig extraction failed\n'
                f'         n = {challenge} ; player = {player_url}', expected=False)

        self.logger.debug(f'Decrypted nsig {challenge} => {ret}')
        # Only cache nsig func JS code to disk if successful, and only once
        self.ie._store_player_data_to_cache('nsig', player_url, func_code)
        return ret

    # region sig
    def _extract_signature_function(self, video_id, player_url, example_sig):
        # Read from filesystem cache
        func_id = join_nonempty(
            self.ie._player_js_cache_key(player_url), self._signature_cache_id(example_sig))
        assert os.path.basename(func_id) == func_id

        self.logger.debug(f'Extracting signature function {func_id}')
        cache_spec, code = self.ie.cache.load('youtube-sigfuncs', func_id, min_ver='2025.07.21'), None

        if not cache_spec:
            code = self._get_player(video_id, player_url)
        if code:
            res = self._parse_sig_js(code, player_url)
            test_string = ''.join(map(chr, range(len(example_sig))))
            cache_spec = [ord(c) for c in res(test_string)]
            self.ie.cache.store('youtube-sigfuncs', func_id, cache_spec)

        return lambda s: ''.join(s[i] for i in cache_spec)

    def _print_sig_code(self, func, example_sig):
        if not self.ie.get_param('youtube_print_sig_code'):
            return

        def gen_sig_code(idxs):
            def _genslice(start, end, step):
                starts = '' if start == 0 else str(start)
                ends = (':%d' % (end + step)) if end + step >= 0 else ':'
                steps = '' if step == 1 else (':%d' % step)
                return f's[{starts}{ends}{steps}]'

            step = None
            # Quelch pyflakes warnings - start will be set when step is set
            start = '(Never used)'
            for i, prev in zip(idxs[1:], idxs[:-1]):
                if step is not None:
                    if i - prev == step:
                        continue
                    yield _genslice(start, prev, step)
                    step = None
                    continue
                if i - prev in [-1, 1]:
                    step = i - prev
                    start = prev
                    continue
                else:
                    yield 's[%d]' % prev
            if step is None:
                yield 's[%d]' % i
            else:
                yield _genslice(start, i, step)

        test_string = ''.join(map(chr, range(len(example_sig))))
        cache_res = func(test_string)
        cache_spec = [ord(c) for c in cache_res]
        expr_code = ' + '.join(gen_sig_code(cache_spec))
        signature_id_tuple = '({})'.format(', '.join(str(len(p)) for p in example_sig.split('.')))
        code = (f'if tuple(len(p) for p in s.split(\'.\')) == {signature_id_tuple}:\n'
                f'    return {expr_code}\n')
        self.logger.info('Extracted signature function:\n' + code)

    def _parse_sig_js(self, jscode, player_url):
        # Examples where `sig` is funcname:
        # sig=function(a){a=a.split(""); ... ;return a.join("")};
        # ;c&&(c=sig(decodeURIComponent(c)),a.set(b,encodeURIComponent(c)));return a};
        # {var l=f,m=h.sp,n=sig(decodeURIComponent(h.s));l.set(m,encodeURIComponent(n))}
        # sig=function(J){J=J.split(""); ... ;return J.join("")};
        # ;N&&(N=sig(decodeURIComponent(N)),J.set(R,encodeURIComponent(N)));return J};
        # {var H=u,k=f.sp,v=sig(decodeURIComponent(f.s));H.set(k,encodeURIComponent(v))}
        funcname = self.ie._search_regex(
            (r'\b(?P<var>[a-zA-Z0-9_$]+)&&\((?P=var)=(?P<sig>[a-zA-Z0-9_$]{2,})\(decodeURIComponent\((?P=var)\)\)',
             r'(?P<sig>[a-zA-Z0-9_$]+)\s*=\s*function\(\s*(?P<arg>[a-zA-Z0-9_$]+)\s*\)\s*{\s*(?P=arg)\s*=\s*(?P=arg)\.split\(\s*""\s*\)\s*;\s*[^}]+;\s*return\s+(?P=arg)\.join\(\s*""\s*\)',
             r'(?:\b|[^a-zA-Z0-9_$])(?P<sig>[a-zA-Z0-9_$]{2,})\s*=\s*function\(\s*a\s*\)\s*{\s*a\s*=\s*a\.split\(\s*""\s*\)(?:;[a-zA-Z0-9_$]{2}\.[a-zA-Z0-9_$]{2}\(a,\d+\))?',
             # Old patterns
             r'\b[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*encodeURIComponent\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\b[a-zA-Z0-9]+\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*encodeURIComponent\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\bm=(?P<sig>[a-zA-Z0-9$]{2,})\(decodeURIComponent\(h\.s\)\)',
             # Obsolete patterns
             r'("|\')signature\1\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\.sig\|\|(?P<sig>[a-zA-Z0-9$]+)\(',
             r'yt\.akamaized\.net/\)\s*\|\|\s*.*?\s*[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*(?:encodeURIComponent\s*\()?\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\b[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\bc\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\('),
            jscode, 'Initial JS player signature function name', group='sig')

        varname, global_list = self._interpret_player_js_global_var(jscode, player_url)
        jsi = JSInterpreter(jscode)
        initial_function = jsi.extract_function(funcname, filter_dict({varname: global_list}))
        return lambda s: initial_function([s])

    def _signature_cache_id(self, example_sig):
        """ Return a string representation of a signature """
        return '.'.join(str(len(part)) for part in example_sig.split('.'))

    # endregion sig

    # region nsig

    def _extract_n_function_name(self, jscode, player_url=None):
        varname, global_list = self._interpret_player_js_global_var(jscode, player_url)
        if debug_str := traverse_obj(global_list, (lambda _, v: v.endswith('-_w8_'), any)):
            pattern = r'''(?x)
                \{\s*return\s+%s\[%d\]\s*\+\s*(?P<argname>[a-zA-Z0-9_$]+)\s*\}
            ''' % (re.escape(varname), global_list.index(debug_str))
            if match := re.search(pattern, jscode):
                pattern = r'''(?x)
                    \{\s*\)%s\(\s*
                    (?:
                        (?P<funcname_a>[a-zA-Z0-9_$]+)\s*noitcnuf\s*
                        |noitcnuf\s*=\s*(?P<funcname_b>[a-zA-Z0-9_$]+)(?:\s+rav)?
                    )[;\n]
                ''' % re.escape(match.group('argname')[::-1])
                if match := re.search(pattern, jscode[match.start()::-1]):
                    a, b = match.group('funcname_a', 'funcname_b')
                    return (a or b)[::-1]
            # TODO: only print once
            self.logger.debug(join_nonempty(
                'Initial search was unable to find nsig function name',
                player_url and f'        player = {player_url}', delim='\n'))

        # Examples (with placeholders nfunc, narray, idx):
        # *  .get("n"))&&(b=nfunc(b)
        # *  .get("n"))&&(b=narray[idx](b)
        # *  b=String.fromCharCode(110),c=a.get(b))&&c=narray[idx](c)
        # *  a.D&&(b="nn"[+a.D],c=a.get(b))&&(c=narray[idx](c),a.set(b,c),narray.length||nfunc("")
        # *  a.D&&(PL(a),b=a.j.n||null)&&(b=narray[0](b),a.set("n",b),narray.length||nfunc("")
        # *  a.D&&(b="nn"[+a.D],vL(a),c=a.j[b]||null)&&(c=narray[idx](c),a.set(b,c),narray.length||nfunc("")
        # *  J.J="";J.url="";J.Z&&(R="nn"[+J.Z],mW(J),N=J.K[R]||null)&&(N=narray[idx](N),J.set(R,N))}};
        funcname, idx = self.ie._search_regex(
            r'''(?x)
            (?:
                \.get\("n"\)\)&&\(b=|
                (?:
                    b=String\.fromCharCode\(110\)|
                    (?P<str_idx>[a-zA-Z0-9_$.]+)&&\(b="nn"\[\+(?P=str_idx)\]
                )
                (?:
                    ,[a-zA-Z0-9_$]+\(a\))?,c=a\.
                    (?:
                        get\(b\)|
                        [a-zA-Z0-9_$]+\[b\]\|\|null
                    )\)&&\(c=|
                \b(?P<var>[a-zA-Z0-9_$]+)=
            )(?P<nfunc>[a-zA-Z0-9_$]+)(?:\[(?P<idx>\d+)\])?\([a-zA-Z]\)
            (?(var),[a-zA-Z0-9_$]+\.set\((?:"n+"|[a-zA-Z0-9_$]+)\,(?P=var)\))''',
            jscode, 'n function name', group=('nfunc', 'idx'), default=(None, None))
        if not funcname:
            self.logger.warning(join_nonempty(
                'Falling back to generic n function search',
                player_url and f'         player = {player_url}', delim='\n'), once=True)
            return self.ie._search_regex(
                r'''(?xs)
                ;\s*(?P<name>[a-zA-Z0-9_$]+)\s*=\s*function\([a-zA-Z0-9_$]+\)
                \s*\{(?:(?!};).)+?return\s*(?P<q>["'])[\w-]+_w8_(?P=q)\s*\+\s*[a-zA-Z0-9_$]+''',
                jscode, 'Initial JS player n function name', group='name')
        elif not idx:
            return funcname

        return json.loads(js_to_json(self.ie._search_regex(
            rf'var {re.escape(funcname)}\s*=\s*(\[.+?\])\s*[,;]', jscode,
            f'Initial JS player n function list ({funcname}.{idx})')))[int(idx)]

    def _fixup_n_function_code(self, argnames, nsig_code, jscode, player_url):
        # Fixup global array
        varname, global_list = self._interpret_player_js_global_var(jscode, player_url)
        if varname and global_list:
            nsig_code = f'var {varname}={json.dumps(global_list)}; {nsig_code}'
        else:
            varname = self._DUMMY_STRING
            global_list = []

        # Fixup typeof check
        undefined_idx = global_list.index('undefined') if 'undefined' in global_list else r'\d+'
        fixed_code = re.sub(
            fr'''(?x)
                ;\s*if\s*\(\s*typeof\s+[a-zA-Z0-9_$]+\s*===?\s*(?:
                    (["\'])undefined\1|
                    {re.escape(varname)}\[{undefined_idx}\]
                )\s*\)\s*return\s+{re.escape(argnames[0])};
            ''', ';', nsig_code)
        if fixed_code == nsig_code:
            # TODO: only print once
            self.logger.debug(join_nonempty(
                'No typeof statement found in nsig function code',
                player_url and f'        player = {player_url}', delim='\n'))

        # Fixup global funcs
        jsi = JSInterpreter(fixed_code)
        cache_id = (self._NSIG_FUNC_CACHE_ID, player_url)
        try:
            self.ie._cached(
                self._extract_n_function_from_code, *cache_id)(jsi, (argnames, fixed_code))(self._DUMMY_STRING)
        except JSInterpreter.Exception:
            self.ie._player_cache.pop(cache_id, None)

        global_funcnames = jsi._undefined_varnames
        debug_names = []
        jsi = JSInterpreter(jscode)
        for func_name in global_funcnames:
            try:
                func_args, func_code = jsi.extract_function_code(func_name)
                fixed_code = f'var {func_name} = function({", ".join(func_args)}) {{ {func_code} }}; {fixed_code}'
                debug_names.append(func_name)
            except Exception:
                self.logger.warning(join_nonempty(
                    f'Unable to extract global nsig function {func_name} from player JS',
                    player_url and f'        player = {player_url}', delim='\n'), once=True)

        if debug_names:
            self.logger.debug(f'Extracted global nsig functions: {", ".join(debug_names)}')

        return argnames, fixed_code

    def _extract_n_function_code(self, video_id, player_url):
        player_id = self.ie._extract_player_info(player_url)
        func_code = self.ie._load_player_data_from_cache('nsig', player_url)
        jscode = func_code or self.ie._load_player(video_id, player_url)
        jsi = JSInterpreter(jscode)

        if func_code:
            return jsi, player_id, func_code

        func_name = self._extract_n_function_name(jscode, player_url=player_url)

        # XXX: Work around (a) global array variable, (b) `typeof` short-circuit, (c) global functions
        func_code = self._fixup_n_function_code(*jsi.extract_function_code(func_name), jscode, player_url)

        return jsi, player_id, func_code

    def _extract_n_function_from_code(self, jsi, func_code):
        func = jsi.extract_function_from_code(*func_code)

        def extract_nsig(s):
            try:
                ret = func([s])
            except JSInterpreter.Exception:
                raise
            except Exception as e:
                raise JSInterpreter.Exception(traceback.format_exc(), cause=e)

            if ret.startswith('enhanced_except_') or ret.endswith(s):
                raise JSInterpreter.Exception('Signature function returned an exception')
            return ret

        return extract_nsig

    # endregion

    def _interpret_player_js_global_var(self, jscode, player_url):
        """Returns tuple of: variable name string, variable value list"""
        extract_global_var = self.ie._cached(self.ie._search_regex, 'jsc global array', player_url)
        varcode, varname, varvalue = extract_global_var(
            r'''(?x)
                (?P<q1>["\'])use\s+strict(?P=q1);\s*
                (?P<code>
                    var\s+(?P<name>[a-zA-Z0-9_$]+)\s*=\s*
                    (?P<value>
                        (?P<q2>["\'])(?:(?!(?P=q2)).|\\.)+(?P=q2)
                        \.split\((?P<q3>["\'])(?:(?!(?P=q3)).)+(?P=q3)\)
                        |\[\s*(?:(?P<q4>["\'])(?:(?!(?P=q4)).|\\.)*(?P=q4)\s*,?\s*)+\]
                    )
                )[;,]
            ''', jscode, 'global variable', group=('code', 'name', 'value'), default=(None, None, None))
        if not varcode:
            # TODO: only print once
            self.logger.debug(join_nonempty(
                'No global array variable found in player JS',
                player_url and f'        player = {player_url}', delim='\n'))
            return None, None

        jsi = JSInterpreter(varcode)
        interpret_global_var = self.ie._cached(jsi.interpret_expression, 'jsc global list', player_url)
        return varname, interpret_global_var(varvalue, LocalNameSpace(), allow_recursion=10)
