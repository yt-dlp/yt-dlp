import collections
import contextlib
import json
import operator
import re

from .utils import ExtractorError, remove_quotes

_OPERATORS = [
    ('|', operator.or_),
    ('^', operator.xor),
    ('&', operator.and_),
    ('>>', operator.rshift),
    ('<<', operator.lshift),
    ('-', operator.sub),
    ('+', operator.add),
    ('%', operator.mod),
    ('/', operator.truediv),
    ('*', operator.mul),
]
_ASSIGN_OPERATORS = [(op + '=', opfunc) for op, opfunc in _OPERATORS]
_ASSIGN_OPERATORS.append(('=', (lambda cur, right: right)))

_NAME_RE = r'[a-zA-Z_$][a-zA-Z_$0-9]*'

_MATCHING_PARENS = dict(zip('({[', ')}]'))


class JS_Break(ExtractorError):
    def __init__(self):
        ExtractorError.__init__(self, 'Invalid break')


class JS_Continue(ExtractorError):
    def __init__(self):
        ExtractorError.__init__(self, 'Invalid continue')


class LocalNameSpace(collections.ChainMap):
    def __setitem__(self, key, value):
        for scope in self.maps:
            if key in scope:
                scope[key] = value
                return
        self.maps[0][key] = value

    def __delitem__(self, key):
        raise NotImplementedError('Deleting is not supported')


class JSInterpreter:
    def __init__(self, code, objects=None):
        if objects is None:
            objects = {}
        self.code = code
        self._functions = {}
        self._objects = objects
        self.__named_object_counter = 0

    def _named_object(self, namespace, obj):
        self.__named_object_counter += 1
        name = f'__yt_dlp_jsinterp_obj{self.__named_object_counter}'
        namespace[name] = obj
        return name

    @staticmethod
    def _separate(expr, delim=',', max_split=None):
        if not expr:
            return
        counters = {k: 0 for k in _MATCHING_PARENS.values()}
        start, splits, pos, delim_len = 0, 0, 0, len(delim) - 1
        for idx, char in enumerate(expr):
            if char in _MATCHING_PARENS:
                counters[_MATCHING_PARENS[char]] += 1
            elif char in counters:
                counters[char] -= 1
            if char != delim[pos] or any(counters.values()):
                pos = 0
                continue
            elif pos != delim_len:
                pos += 1
                continue
            yield expr[start: idx - delim_len]
            start, pos = idx + 1, 0
            splits += 1
            if max_split and splits >= max_split:
                break
        yield expr[start:]

    @staticmethod
    def _separate_at_paren(expr, delim):
        separated = list(JSInterpreter._separate(expr, delim, 1))
        if len(separated) < 2:
            raise ExtractorError(f'No terminating paren {delim} in {expr}')
        return separated[0][1:].strip(), separated[1].strip()

    def interpret_statement(self, stmt, local_vars, allow_recursion=100):
        if allow_recursion < 0:
            raise ExtractorError('Recursion limit reached')

        sub_statements = list(self._separate(stmt, ';'))
        stmt = (sub_statements or ['']).pop()
        for sub_stmt in sub_statements:
            ret, should_abort = self.interpret_statement(sub_stmt, local_vars, allow_recursion - 1)
            if should_abort:
                return ret

        should_abort = False
        stmt = stmt.lstrip()
        stmt_m = re.match(r'var\s', stmt)
        if stmt_m:
            expr = stmt[len(stmt_m.group(0)):]
        else:
            return_m = re.match(r'return(?:\s+|$)', stmt)
            if return_m:
                expr = stmt[len(return_m.group(0)):]
                should_abort = True
            else:
                # Try interpreting it as an expression
                expr = stmt

        v = self.interpret_expression(expr, local_vars, allow_recursion)
        return v, should_abort

    def interpret_expression(self, expr, local_vars, allow_recursion):
        expr = expr.strip()
        if expr == '':  # Empty expression
            return None

        if expr.startswith('{'):
            inner, outer = self._separate_at_paren(expr, '}')
            inner, should_abort = self.interpret_statement(inner, local_vars, allow_recursion - 1)
            if not outer or should_abort:
                return inner
            else:
                expr = json.dumps(inner) + outer

        if expr.startswith('('):
            inner, outer = self._separate_at_paren(expr, ')')
            inner = self.interpret_expression(inner, local_vars, allow_recursion)
            if not outer:
                return inner
            else:
                expr = json.dumps(inner) + outer

        if expr.startswith('['):
            inner, outer = self._separate_at_paren(expr, ']')
            name = self._named_object(local_vars, [
                self.interpret_expression(item, local_vars, allow_recursion)
                for item in self._separate(inner)])
            expr = name + outer

        m = re.match(r'try\s*', expr)
        if m:
            if expr[m.end()] == '{':
                try_expr, expr = self._separate_at_paren(expr[m.end():], '}')
            else:
                try_expr, expr = expr[m.end() - 1:], ''
            ret, should_abort = self.interpret_statement(try_expr, local_vars, allow_recursion - 1)
            if should_abort:
                return ret
            return self.interpret_statement(expr, local_vars, allow_recursion - 1)[0]

        m = re.match(r'catch\s*\(', expr)
        if m:
            # We ignore the catch block
            _, expr = self._separate_at_paren(expr, '}')
            return self.interpret_statement(expr, local_vars, allow_recursion - 1)[0]

        m = re.match(r'for\s*\(', expr)
        if m:
            constructor, remaining = self._separate_at_paren(expr[m.end() - 1:], ')')
            if remaining.startswith('{'):
                body, expr = self._separate_at_paren(remaining, '}')
            else:
                m = re.match(r'switch\s*\(', remaining)  # FIXME
                if m:
                    switch_val, remaining = self._separate_at_paren(remaining[m.end() - 1:], ')')
                    body, expr = self._separate_at_paren(remaining, '}')
                    body = 'switch(%s){%s}' % (switch_val, body)
                else:
                    body, expr = remaining, ''
            start, cndn, increment = self._separate(constructor, ';')
            if self.interpret_statement(start, local_vars, allow_recursion - 1)[1]:
                raise ExtractorError(
                    f'Premature return in the initialization of a for loop in {constructor!r}')
            while True:
                if not self.interpret_expression(cndn, local_vars, allow_recursion):
                    break
                try:
                    ret, should_abort = self.interpret_statement(body, local_vars, allow_recursion - 1)
                    if should_abort:
                        return ret
                except JS_Break:
                    break
                except JS_Continue:
                    pass
                if self.interpret_statement(increment, local_vars, allow_recursion - 1)[1]:
                    raise ExtractorError(
                        f'Premature return in the initialization of a for loop in {constructor!r}')
            return self.interpret_statement(expr, local_vars, allow_recursion - 1)[0]

        m = re.match(r'switch\s*\(', expr)
        if m:
            switch_val, remaining = self._separate_at_paren(expr[m.end() - 1:], ')')
            switch_val = self.interpret_expression(switch_val, local_vars, allow_recursion)
            body, expr = self._separate_at_paren(remaining, '}')
            items = body.replace('default:', 'case default:').split('case ')[1:]
            for default in (False, True):
                matched = False
                for item in items:
                    case, stmt = (i.strip() for i in self._separate(item, ':', 1))
                    if default:
                        matched = matched or case == 'default'
                    elif not matched:
                        matched = case != 'default' and switch_val == self.interpret_expression(case, local_vars, allow_recursion)
                    if not matched:
                        continue
                    try:
                        ret, should_abort = self.interpret_statement(stmt, local_vars, allow_recursion - 1)
                        if should_abort:
                            return ret
                    except JS_Break:
                        break
                if matched:
                    break
            return self.interpret_statement(expr, local_vars, allow_recursion - 1)[0]

        # Comma separated statements
        sub_expressions = list(self._separate(expr))
        expr = sub_expressions.pop().strip() if sub_expressions else ''
        for sub_expr in sub_expressions:
            self.interpret_expression(sub_expr, local_vars, allow_recursion)

        for m in re.finditer(rf'''(?x)
                (?P<pre_sign>\+\+|--)(?P<var1>{_NAME_RE})|
                (?P<var2>{_NAME_RE})(?P<post_sign>\+\+|--)''', expr):
            var = m.group('var1') or m.group('var2')
            start, end = m.span()
            sign = m.group('pre_sign') or m.group('post_sign')
            ret = local_vars[var]
            local_vars[var] += 1 if sign[0] == '+' else -1
            if m.group('pre_sign'):
                ret = local_vars[var]
            expr = expr[:start] + json.dumps(ret) + expr[end:]

        for op, opfunc in _ASSIGN_OPERATORS:
            m = re.match(rf'''(?x)
                (?P<out>{_NAME_RE})(?:\[(?P<index>[^\]]+?)\])?
                \s*{re.escape(op)}
                (?P<expr>.*)$''', expr)
            if not m:
                continue
            right_val = self.interpret_expression(m.group('expr'), local_vars, allow_recursion)

            if m.groupdict().get('index'):
                lvar = local_vars[m.group('out')]
                idx = self.interpret_expression(m.group('index'), local_vars, allow_recursion)
                if not isinstance(idx, int):
                    raise ExtractorError(f'List indices must be integers: {idx}')
                cur = lvar[idx]
                val = opfunc(cur, right_val)
                lvar[idx] = val
                return val
            else:
                cur = local_vars.get(m.group('out'))
                val = opfunc(cur, right_val)
                local_vars[m.group('out')] = val
                return val

        if expr.isdigit():
            return int(expr)

        if expr == 'break':
            raise JS_Break()
        elif expr == 'continue':
            raise JS_Continue()

        var_m = re.match(
            r'(?!if|return|true|false|null)(?P<name>%s)$' % _NAME_RE,
            expr)
        if var_m:
            return local_vars[var_m.group('name')]

        with contextlib.suppress(ValueError):
            return json.loads(expr)

        m = re.match(
            r'(?P<in>%s)\[(?P<idx>.+)\]$' % _NAME_RE, expr)
        if m:
            val = local_vars[m.group('in')]
            idx = self.interpret_expression(m.group('idx'), local_vars, allow_recursion)
            return val[idx]

        for op, opfunc in _OPERATORS:
            separated = list(self._separate(expr, op))
            if len(separated) < 2:
                continue
            right_val = separated.pop()
            left_val = op.join(separated)
            left_val, should_abort = self.interpret_statement(
                left_val, local_vars, allow_recursion - 1)
            if should_abort:
                raise ExtractorError(f'Premature left-side return of {op} in {expr!r}')
            right_val, should_abort = self.interpret_statement(
                right_val, local_vars, allow_recursion - 1)
            if should_abort:
                raise ExtractorError(f'Premature right-side return of {op} in {expr!r}')
            return opfunc(left_val or 0, right_val)

        m = re.match(
            r'(?P<var>%s)(?:\.(?P<member>[^(]+)|\[(?P<member2>[^]]+)\])\s*' % _NAME_RE,
            expr)
        if m:
            variable = m.group('var')
            member = remove_quotes(m.group('member') or m.group('member2'))
            arg_str = expr[m.end():]
            if arg_str.startswith('('):
                arg_str, remaining = self._separate_at_paren(arg_str, ')')
            else:
                arg_str, remaining = None, arg_str

            def assertion(cndn, msg):
                """ assert, but without risk of getting optimized out """
                if not cndn:
                    raise ExtractorError(f'{member} {msg}: {expr}')

            def eval_method():
                nonlocal member
                if variable == 'String':
                    obj = str
                elif variable in local_vars:
                    obj = local_vars[variable]
                else:
                    if variable not in self._objects:
                        self._objects[variable] = self.extract_object(variable)
                    obj = self._objects[variable]

                if arg_str is None:
                    # Member access
                    if member == 'length':
                        return len(obj)
                    return obj[member]

                # Function call
                argvals = [
                    self.interpret_expression(v, local_vars, allow_recursion)
                    for v in self._separate(arg_str)]

                if obj == str:
                    if member == 'fromCharCode':
                        assertion(argvals, 'takes one or more arguments')
                        return ''.join(map(chr, argvals))
                    raise ExtractorError(f'Unsupported string method {member}')

                if member == 'split':
                    assertion(argvals, 'takes one or more arguments')
                    assertion(argvals == [''], 'with arguments is not implemented')
                    return list(obj)
                elif member == 'join':
                    assertion(isinstance(obj, list), 'must be applied on a list')
                    assertion(len(argvals) == 1, 'takes exactly one argument')
                    return argvals[0].join(obj)
                elif member == 'reverse':
                    assertion(not argvals, 'does not take any arguments')
                    obj.reverse()
                    return obj
                elif member == 'slice':
                    assertion(isinstance(obj, list), 'must be applied on a list')
                    assertion(len(argvals) == 1, 'takes exactly one argument')
                    return obj[argvals[0]:]
                elif member == 'splice':
                    assertion(isinstance(obj, list), 'must be applied on a list')
                    assertion(argvals, 'takes one or more arguments')
                    index, howMany = map(int, (argvals + [len(obj)])[:2])
                    if index < 0:
                        index += len(obj)
                    add_items = argvals[2:]
                    res = []
                    for i in range(index, min(index + howMany, len(obj))):
                        res.append(obj.pop(index))
                    for i, item in enumerate(add_items):
                        obj.insert(index + i, item)
                    return res
                elif member == 'unshift':
                    assertion(isinstance(obj, list), 'must be applied on a list')
                    assertion(argvals, 'takes one or more arguments')
                    for item in reversed(argvals):
                        obj.insert(0, item)
                    return obj
                elif member == 'pop':
                    assertion(isinstance(obj, list), 'must be applied on a list')
                    assertion(not argvals, 'does not take any arguments')
                    if not obj:
                        return
                    return obj.pop()
                elif member == 'push':
                    assertion(argvals, 'takes one or more arguments')
                    obj.extend(argvals)
                    return obj
                elif member == 'forEach':
                    assertion(argvals, 'takes one or more arguments')
                    assertion(len(argvals) <= 2, 'takes at-most 2 arguments')
                    f, this = (argvals + [''])[:2]
                    return [f((item, idx, obj), this=this) for idx, item in enumerate(obj)]
                elif member == 'indexOf':
                    assertion(argvals, 'takes one or more arguments')
                    assertion(len(argvals) <= 2, 'takes at-most 2 arguments')
                    idx, start = (argvals + [0])[:2]
                    try:
                        return obj.index(idx, start)
                    except ValueError:
                        return -1

                if isinstance(obj, list):
                    member = int(member)
                return obj[member](argvals)

            if remaining:
                return self.interpret_expression(
                    self._named_object(local_vars, eval_method()) + remaining,
                    local_vars, allow_recursion)
            else:
                return eval_method()

        m = re.match(r'^(?P<func>%s)\((?P<args>[a-zA-Z0-9_$,]*)\)$' % _NAME_RE, expr)
        if m:
            fname = m.group('func')
            argvals = tuple(
                int(v) if v.isdigit() else local_vars[v]
                for v in self._separate(m.group('args')))
            if fname in local_vars:
                return local_vars[fname](argvals)
            elif fname not in self._functions:
                self._functions[fname] = self.extract_function(fname)
            return self._functions[fname](argvals)

        if expr:
            raise ExtractorError('Unsupported JS expression %r' % expr)

    def extract_object(self, objname):
        _FUNC_NAME_RE = r'''(?:[a-zA-Z$0-9]+|"[a-zA-Z$0-9]+"|'[a-zA-Z$0-9]+')'''
        obj = {}
        obj_m = re.search(
            r'''(?x)
                (?<!this\.)%s\s*=\s*{\s*
                    (?P<fields>(%s\s*:\s*function\s*\(.*?\)\s*{.*?}(?:,\s*)?)*)
                }\s*;
            ''' % (re.escape(objname), _FUNC_NAME_RE),
            self.code)
        fields = obj_m.group('fields')
        # Currently, it only supports function definitions
        fields_m = re.finditer(
            r'''(?x)
                (?P<key>%s)\s*:\s*function\s*\((?P<args>[a-z,]+)\){(?P<code>[^}]+)}
            ''' % _FUNC_NAME_RE,
            fields)
        for f in fields_m:
            argnames = f.group('args').split(',')
            obj[remove_quotes(f.group('key'))] = self.build_function(argnames, f.group('code'))

        return obj

    def extract_function_code(self, funcname):
        """ @returns argnames, code """
        func_m = re.search(
            r'''(?x)
                (?:function\s+%s|[{;,]\s*%s\s*=\s*function|var\s+%s\s*=\s*function)\s*
                \((?P<args>[^)]*)\)\s*
                (?P<code>\{(?:(?!};)[^"]|"([^"]|\\")*")+\})''' % (
                re.escape(funcname), re.escape(funcname), re.escape(funcname)),
            self.code)
        code, _ = self._separate_at_paren(func_m.group('code'), '}')  # refine the match
        if func_m is None:
            raise ExtractorError('Could not find JS function %r' % funcname)
        return func_m.group('args').split(','), code

    def extract_function(self, funcname):
        return self.extract_function_from_code(*self.extract_function_code(funcname))

    def extract_function_from_code(self, argnames, code, *global_stack):
        local_vars = {}
        while True:
            mobj = re.search(r'function\((?P<args>[^)]*)\)\s*{', code)
            if mobj is None:
                break
            start, body_start = mobj.span()
            body, remaining = self._separate_at_paren(code[body_start - 1:], '}')
            name = self._named_object(
                local_vars,
                self.extract_function_from_code(
                    [str.strip(x) for x in mobj.group('args').split(',')],
                    body, local_vars, *global_stack))
            code = code[:start] + name + remaining
        return self.build_function(argnames, code, local_vars, *global_stack)

    def call_function(self, funcname, *args):
        return self.extract_function(funcname)(args)

    def build_function(self, argnames, code, *global_stack):
        global_stack = list(global_stack) or [{}]

        def resf(args, **kwargs):
            global_stack[0].update({
                **dict(zip(argnames, args)),
                **kwargs
            })
            var_stack = LocalNameSpace(*global_stack)
            for stmt in self._separate(code.replace('\n', ''), ';'):
                ret, should_abort = self.interpret_statement(stmt, var_stack)
                if should_abort:
                    break
            return ret
        return resf
