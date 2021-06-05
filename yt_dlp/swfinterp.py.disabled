from __future__ import unicode_literals

import collections
import io
import zlib

from .compat import (
    compat_str,
    compat_struct_unpack,
)
from .utils import (
    ExtractorError,
)


def _extract_tags(file_contents):
    if file_contents[1:3] != b'WS':
        raise ExtractorError(
            'Not an SWF file; header is %r' % file_contents[:3])
    if file_contents[:1] == b'C':
        content = zlib.decompress(file_contents[8:])
    else:
        raise NotImplementedError(
            'Unsupported compression format %r' %
            file_contents[:1])

    # Determine number of bits in framesize rectangle
    framesize_nbits = compat_struct_unpack('!B', content[:1])[0] >> 3
    framesize_len = (5 + 4 * framesize_nbits + 7) // 8

    pos = framesize_len + 2 + 2
    while pos < len(content):
        header16 = compat_struct_unpack('<H', content[pos:pos + 2])[0]
        pos += 2
        tag_code = header16 >> 6
        tag_len = header16 & 0x3f
        if tag_len == 0x3f:
            tag_len = compat_struct_unpack('<I', content[pos:pos + 4])[0]
            pos += 4
        assert pos + tag_len <= len(content), \
            ('Tag %d ends at %d+%d - that\'s longer than the file (%d)'
                % (tag_code, pos, tag_len, len(content)))
        yield (tag_code, content[pos:pos + tag_len])
        pos += tag_len


class _AVMClass_Object(object):
    def __init__(self, avm_class):
        self.avm_class = avm_class

    def __repr__(self):
        return '%s#%x' % (self.avm_class.name, id(self))


class _ScopeDict(dict):
    def __init__(self, avm_class):
        super(_ScopeDict, self).__init__()
        self.avm_class = avm_class

    def __repr__(self):
        return '%s__Scope(%s)' % (
            self.avm_class.name,
            super(_ScopeDict, self).__repr__())


class _AVMClass(object):
    def __init__(self, name_idx, name, static_properties=None):
        self.name_idx = name_idx
        self.name = name
        self.method_names = {}
        self.method_idxs = {}
        self.methods = {}
        self.method_pyfunctions = {}
        self.static_properties = static_properties if static_properties else {}

        self.variables = _ScopeDict(self)
        self.constants = {}

    def make_object(self):
        return _AVMClass_Object(self)

    def __repr__(self):
        return '_AVMClass(%s)' % (self.name)

    def register_methods(self, methods):
        self.method_names.update(methods.items())
        self.method_idxs.update(dict(
            (idx, name)
            for name, idx in methods.items()))


class _Multiname(object):
    def __init__(self, kind):
        self.kind = kind

    def __repr__(self):
        return '[MULTINAME kind: 0x%x]' % self.kind


def _read_int(reader):
    res = 0
    shift = 0
    for _ in range(5):
        buf = reader.read(1)
        assert len(buf) == 1
        b = compat_struct_unpack('<B', buf)[0]
        res = res | ((b & 0x7f) << shift)
        if b & 0x80 == 0:
            break
        shift += 7
    return res


def _u30(reader):
    res = _read_int(reader)
    assert res & 0xf0000000 == 0
    return res


_u32 = _read_int


def _s32(reader):
    v = _read_int(reader)
    if v & 0x80000000 != 0:
        v = - ((v ^ 0xffffffff) + 1)
    return v


def _s24(reader):
    bs = reader.read(3)
    assert len(bs) == 3
    last_byte = b'\xff' if (ord(bs[2:3]) >= 0x80) else b'\x00'
    return compat_struct_unpack('<i', bs + last_byte)[0]


def _read_string(reader):
    slen = _u30(reader)
    resb = reader.read(slen)
    assert len(resb) == slen
    return resb.decode('utf-8')


def _read_bytes(count, reader):
    assert count >= 0
    resb = reader.read(count)
    assert len(resb) == count
    return resb


def _read_byte(reader):
    resb = _read_bytes(1, reader=reader)
    res = compat_struct_unpack('<B', resb)[0]
    return res


StringClass = _AVMClass('(no name idx)', 'String')
ByteArrayClass = _AVMClass('(no name idx)', 'ByteArray')
TimerClass = _AVMClass('(no name idx)', 'Timer')
TimerEventClass = _AVMClass('(no name idx)', 'TimerEvent', {'TIMER': 'timer'})
_builtin_classes = {
    StringClass.name: StringClass,
    ByteArrayClass.name: ByteArrayClass,
    TimerClass.name: TimerClass,
    TimerEventClass.name: TimerEventClass,
}


class _Undefined(object):
    def __bool__(self):
        return False
    __nonzero__ = __bool__

    def __hash__(self):
        return 0

    def __str__(self):
        return 'undefined'
    __repr__ = __str__


undefined = _Undefined()


class SWFInterpreter(object):
    def __init__(self, file_contents):
        self._patched_functions = {
            (TimerClass, 'addEventListener'): lambda params: undefined,
        }
        code_tag = next(tag
                        for tag_code, tag in _extract_tags(file_contents)
                        if tag_code == 82)
        p = code_tag.index(b'\0', 4) + 1
        code_reader = io.BytesIO(code_tag[p:])

        # Parse ABC (AVM2 ByteCode)

        # Define a couple convenience methods
        u30 = lambda *args: _u30(*args, reader=code_reader)
        s32 = lambda *args: _s32(*args, reader=code_reader)
        u32 = lambda *args: _u32(*args, reader=code_reader)
        read_bytes = lambda *args: _read_bytes(*args, reader=code_reader)
        read_byte = lambda *args: _read_byte(*args, reader=code_reader)

        # minor_version + major_version
        read_bytes(2 + 2)

        # Constant pool
        int_count = u30()
        self.constant_ints = [0]
        for _c in range(1, int_count):
            self.constant_ints.append(s32())
        self.constant_uints = [0]
        uint_count = u30()
        for _c in range(1, uint_count):
            self.constant_uints.append(u32())
        double_count = u30()
        read_bytes(max(0, (double_count - 1)) * 8)
        string_count = u30()
        self.constant_strings = ['']
        for _c in range(1, string_count):
            s = _read_string(code_reader)
            self.constant_strings.append(s)
        namespace_count = u30()
        for _c in range(1, namespace_count):
            read_bytes(1)  # kind
            u30()  # name
        ns_set_count = u30()
        for _c in range(1, ns_set_count):
            count = u30()
            for _c2 in range(count):
                u30()
        multiname_count = u30()
        MULTINAME_SIZES = {
            0x07: 2,  # QName
            0x0d: 2,  # QNameA
            0x0f: 1,  # RTQName
            0x10: 1,  # RTQNameA
            0x11: 0,  # RTQNameL
            0x12: 0,  # RTQNameLA
            0x09: 2,  # Multiname
            0x0e: 2,  # MultinameA
            0x1b: 1,  # MultinameL
            0x1c: 1,  # MultinameLA
        }
        self.multinames = ['']
        for _c in range(1, multiname_count):
            kind = u30()
            assert kind in MULTINAME_SIZES, 'Invalid multiname kind %r' % kind
            if kind == 0x07:
                u30()  # namespace_idx
                name_idx = u30()
                self.multinames.append(self.constant_strings[name_idx])
            elif kind == 0x09:
                name_idx = u30()
                u30()
                self.multinames.append(self.constant_strings[name_idx])
            else:
                self.multinames.append(_Multiname(kind))
                for _c2 in range(MULTINAME_SIZES[kind]):
                    u30()

        # Methods
        method_count = u30()
        MethodInfo = collections.namedtuple(
            'MethodInfo',
            ['NEED_ARGUMENTS', 'NEED_REST'])
        method_infos = []
        for method_id in range(method_count):
            param_count = u30()
            u30()  # return type
            for _ in range(param_count):
                u30()  # param type
            u30()  # name index (always 0 for youtube)
            flags = read_byte()
            if flags & 0x08 != 0:
                # Options present
                option_count = u30()
                for c in range(option_count):
                    u30()  # val
                    read_bytes(1)  # kind
            if flags & 0x80 != 0:
                # Param names present
                for _ in range(param_count):
                    u30()  # param name
            mi = MethodInfo(flags & 0x01 != 0, flags & 0x04 != 0)
            method_infos.append(mi)

        # Metadata
        metadata_count = u30()
        for _c in range(metadata_count):
            u30()  # name
            item_count = u30()
            for _c2 in range(item_count):
                u30()  # key
                u30()  # value

        def parse_traits_info():
            trait_name_idx = u30()
            kind_full = read_byte()
            kind = kind_full & 0x0f
            attrs = kind_full >> 4
            methods = {}
            constants = None
            if kind == 0x00:  # Slot
                u30()  # Slot id
                u30()  # type_name_idx
                vindex = u30()
                if vindex != 0:
                    read_byte()  # vkind
            elif kind == 0x06:  # Const
                u30()  # Slot id
                u30()  # type_name_idx
                vindex = u30()
                vkind = 'any'
                if vindex != 0:
                    vkind = read_byte()
                if vkind == 0x03:  # Constant_Int
                    value = self.constant_ints[vindex]
                elif vkind == 0x04:  # Constant_UInt
                    value = self.constant_uints[vindex]
                else:
                    return {}, None  # Ignore silently for now
                constants = {self.multinames[trait_name_idx]: value}
            elif kind in (0x01, 0x02, 0x03):  # Method / Getter / Setter
                u30()  # disp_id
                method_idx = u30()
                methods[self.multinames[trait_name_idx]] = method_idx
            elif kind == 0x04:  # Class
                u30()  # slot_id
                u30()  # classi
            elif kind == 0x05:  # Function
                u30()  # slot_id
                function_idx = u30()
                methods[function_idx] = self.multinames[trait_name_idx]
            else:
                raise ExtractorError('Unsupported trait kind %d' % kind)

            if attrs & 0x4 != 0:  # Metadata present
                metadata_count = u30()
                for _c3 in range(metadata_count):
                    u30()  # metadata index

            return methods, constants

        # Classes
        class_count = u30()
        classes = []
        for class_id in range(class_count):
            name_idx = u30()

            cname = self.multinames[name_idx]
            avm_class = _AVMClass(name_idx, cname)
            classes.append(avm_class)

            u30()  # super_name idx
            flags = read_byte()
            if flags & 0x08 != 0:  # Protected namespace is present
                u30()  # protected_ns_idx
            intrf_count = u30()
            for _c2 in range(intrf_count):
                u30()
            u30()  # iinit
            trait_count = u30()
            for _c2 in range(trait_count):
                trait_methods, trait_constants = parse_traits_info()
                avm_class.register_methods(trait_methods)
                if trait_constants:
                    avm_class.constants.update(trait_constants)

        assert len(classes) == class_count
        self._classes_by_name = dict((c.name, c) for c in classes)

        for avm_class in classes:
            avm_class.cinit_idx = u30()
            trait_count = u30()
            for _c2 in range(trait_count):
                trait_methods, trait_constants = parse_traits_info()
                avm_class.register_methods(trait_methods)
                if trait_constants:
                    avm_class.constants.update(trait_constants)

        # Scripts
        script_count = u30()
        for _c in range(script_count):
            u30()  # init
            trait_count = u30()
            for _c2 in range(trait_count):
                parse_traits_info()

        # Method bodies
        method_body_count = u30()
        Method = collections.namedtuple('Method', ['code', 'local_count'])
        self._all_methods = []
        for _c in range(method_body_count):
            method_idx = u30()
            u30()  # max_stack
            local_count = u30()
            u30()  # init_scope_depth
            u30()  # max_scope_depth
            code_length = u30()
            code = read_bytes(code_length)
            m = Method(code, local_count)
            self._all_methods.append(m)
            for avm_class in classes:
                if method_idx in avm_class.method_idxs:
                    avm_class.methods[avm_class.method_idxs[method_idx]] = m
            exception_count = u30()
            for _c2 in range(exception_count):
                u30()  # from
                u30()  # to
                u30()  # target
                u30()  # exc_type
                u30()  # var_name
            trait_count = u30()
            for _c2 in range(trait_count):
                parse_traits_info()

        assert p + code_reader.tell() == len(code_tag)

    def patch_function(self, avm_class, func_name, f):
        self._patched_functions[(avm_class, func_name)] = f

    def extract_class(self, class_name, call_cinit=True):
        try:
            res = self._classes_by_name[class_name]
        except KeyError:
            raise ExtractorError('Class %r not found' % class_name)

        if call_cinit and hasattr(res, 'cinit_idx'):
            res.register_methods({'$cinit': res.cinit_idx})
            res.methods['$cinit'] = self._all_methods[res.cinit_idx]
            cinit = self.extract_function(res, '$cinit')
            cinit([])

        return res

    def extract_function(self, avm_class, func_name):
        p = self._patched_functions.get((avm_class, func_name))
        if p:
            return p
        if func_name in avm_class.method_pyfunctions:
            return avm_class.method_pyfunctions[func_name]
        if func_name in self._classes_by_name:
            return self._classes_by_name[func_name].make_object()
        if func_name not in avm_class.methods:
            raise ExtractorError('Cannot find function %s.%s' % (
                avm_class.name, func_name))
        m = avm_class.methods[func_name]

        def resfunc(args):
            # Helper functions
            coder = io.BytesIO(m.code)
            s24 = lambda: _s24(coder)
            u30 = lambda: _u30(coder)

            registers = [avm_class.variables] + list(args) + [None] * m.local_count
            stack = []
            scopes = collections.deque([
                self._classes_by_name, avm_class.constants, avm_class.variables])
            while True:
                opcode = _read_byte(coder)
                if opcode == 9:  # label
                    pass  # Spec says: "Do nothing."
                elif opcode == 16:  # jump
                    offset = s24()
                    coder.seek(coder.tell() + offset)
                elif opcode == 17:  # iftrue
                    offset = s24()
                    value = stack.pop()
                    if value:
                        coder.seek(coder.tell() + offset)
                elif opcode == 18:  # iffalse
                    offset = s24()
                    value = stack.pop()
                    if not value:
                        coder.seek(coder.tell() + offset)
                elif opcode == 19:  # ifeq
                    offset = s24()
                    value2 = stack.pop()
                    value1 = stack.pop()
                    if value2 == value1:
                        coder.seek(coder.tell() + offset)
                elif opcode == 20:  # ifne
                    offset = s24()
                    value2 = stack.pop()
                    value1 = stack.pop()
                    if value2 != value1:
                        coder.seek(coder.tell() + offset)
                elif opcode == 21:  # iflt
                    offset = s24()
                    value2 = stack.pop()
                    value1 = stack.pop()
                    if value1 < value2:
                        coder.seek(coder.tell() + offset)
                elif opcode == 32:  # pushnull
                    stack.append(None)
                elif opcode == 33:  # pushundefined
                    stack.append(undefined)
                elif opcode == 36:  # pushbyte
                    v = _read_byte(coder)
                    stack.append(v)
                elif opcode == 37:  # pushshort
                    v = u30()
                    stack.append(v)
                elif opcode == 38:  # pushtrue
                    stack.append(True)
                elif opcode == 39:  # pushfalse
                    stack.append(False)
                elif opcode == 40:  # pushnan
                    stack.append(float('NaN'))
                elif opcode == 42:  # dup
                    value = stack[-1]
                    stack.append(value)
                elif opcode == 44:  # pushstring
                    idx = u30()
                    stack.append(self.constant_strings[idx])
                elif opcode == 48:  # pushscope
                    new_scope = stack.pop()
                    scopes.append(new_scope)
                elif opcode == 66:  # construct
                    arg_count = u30()
                    args = list(reversed(
                        [stack.pop() for _ in range(arg_count)]))
                    obj = stack.pop()
                    res = obj.avm_class.make_object()
                    stack.append(res)
                elif opcode == 70:  # callproperty
                    index = u30()
                    mname = self.multinames[index]
                    arg_count = u30()
                    args = list(reversed(
                        [stack.pop() for _ in range(arg_count)]))
                    obj = stack.pop()

                    if obj == StringClass:
                        if mname == 'String':
                            assert len(args) == 1
                            assert isinstance(args[0], (
                                int, compat_str, _Undefined))
                            if args[0] == undefined:
                                res = 'undefined'
                            else:
                                res = compat_str(args[0])
                            stack.append(res)
                            continue
                        else:
                            raise NotImplementedError(
                                'Function String.%s is not yet implemented'
                                % mname)
                    elif isinstance(obj, _AVMClass_Object):
                        func = self.extract_function(obj.avm_class, mname)
                        res = func(args)
                        stack.append(res)
                        continue
                    elif isinstance(obj, _AVMClass):
                        func = self.extract_function(obj, mname)
                        res = func(args)
                        stack.append(res)
                        continue
                    elif isinstance(obj, _ScopeDict):
                        if mname in obj.avm_class.method_names:
                            func = self.extract_function(obj.avm_class, mname)
                            res = func(args)
                        else:
                            res = obj[mname]
                        stack.append(res)
                        continue
                    elif isinstance(obj, compat_str):
                        if mname == 'split':
                            assert len(args) == 1
                            assert isinstance(args[0], compat_str)
                            if args[0] == '':
                                res = list(obj)
                            else:
                                res = obj.split(args[0])
                            stack.append(res)
                            continue
                        elif mname == 'charCodeAt':
                            assert len(args) <= 1
                            idx = 0 if len(args) == 0 else args[0]
                            assert isinstance(idx, int)
                            res = ord(obj[idx])
                            stack.append(res)
                            continue
                    elif isinstance(obj, list):
                        if mname == 'slice':
                            assert len(args) == 1
                            assert isinstance(args[0], int)
                            res = obj[args[0]:]
                            stack.append(res)
                            continue
                        elif mname == 'join':
                            assert len(args) == 1
                            assert isinstance(args[0], compat_str)
                            res = args[0].join(obj)
                            stack.append(res)
                            continue
                    raise NotImplementedError(
                        'Unsupported property %r on %r'
                        % (mname, obj))
                elif opcode == 71:  # returnvoid
                    res = undefined
                    return res
                elif opcode == 72:  # returnvalue
                    res = stack.pop()
                    return res
                elif opcode == 73:  # constructsuper
                    # Not yet implemented, just hope it works without it
                    arg_count = u30()
                    args = list(reversed(
                        [stack.pop() for _ in range(arg_count)]))
                    obj = stack.pop()
                elif opcode == 74:  # constructproperty
                    index = u30()
                    arg_count = u30()
                    args = list(reversed(
                        [stack.pop() for _ in range(arg_count)]))
                    obj = stack.pop()

                    mname = self.multinames[index]
                    assert isinstance(obj, _AVMClass)

                    # We do not actually call the constructor for now;
                    # we just pretend it does nothing
                    stack.append(obj.make_object())
                elif opcode == 79:  # callpropvoid
                    index = u30()
                    mname = self.multinames[index]
                    arg_count = u30()
                    args = list(reversed(
                        [stack.pop() for _ in range(arg_count)]))
                    obj = stack.pop()
                    if isinstance(obj, _AVMClass_Object):
                        func = self.extract_function(obj.avm_class, mname)
                        res = func(args)
                        assert res is undefined
                        continue
                    if isinstance(obj, _ScopeDict):
                        assert mname in obj.avm_class.method_names
                        func = self.extract_function(obj.avm_class, mname)
                        res = func(args)
                        assert res is undefined
                        continue
                    if mname == 'reverse':
                        assert isinstance(obj, list)
                        obj.reverse()
                    else:
                        raise NotImplementedError(
                            'Unsupported (void) property %r on %r'
                            % (mname, obj))
                elif opcode == 86:  # newarray
                    arg_count = u30()
                    arr = []
                    for i in range(arg_count):
                        arr.append(stack.pop())
                    arr = arr[::-1]
                    stack.append(arr)
                elif opcode == 93:  # findpropstrict
                    index = u30()
                    mname = self.multinames[index]
                    for s in reversed(scopes):
                        if mname in s:
                            res = s
                            break
                    else:
                        res = scopes[0]
                    if mname not in res and mname in _builtin_classes:
                        stack.append(_builtin_classes[mname])
                    else:
                        stack.append(res[mname])
                elif opcode == 94:  # findproperty
                    index = u30()
                    mname = self.multinames[index]
                    for s in reversed(scopes):
                        if mname in s:
                            res = s
                            break
                    else:
                        res = avm_class.variables
                    stack.append(res)
                elif opcode == 96:  # getlex
                    index = u30()
                    mname = self.multinames[index]
                    for s in reversed(scopes):
                        if mname in s:
                            scope = s
                            break
                    else:
                        scope = avm_class.variables

                    if mname in scope:
                        res = scope[mname]
                    elif mname in _builtin_classes:
                        res = _builtin_classes[mname]
                    else:
                        # Assume uninitialized
                        # TODO warn here
                        res = undefined
                    stack.append(res)
                elif opcode == 97:  # setproperty
                    index = u30()
                    value = stack.pop()
                    idx = self.multinames[index]
                    if isinstance(idx, _Multiname):
                        idx = stack.pop()
                    obj = stack.pop()
                    obj[idx] = value
                elif opcode == 98:  # getlocal
                    index = u30()
                    stack.append(registers[index])
                elif opcode == 99:  # setlocal
                    index = u30()
                    value = stack.pop()
                    registers[index] = value
                elif opcode == 102:  # getproperty
                    index = u30()
                    pname = self.multinames[index]
                    if pname == 'length':
                        obj = stack.pop()
                        assert isinstance(obj, (compat_str, list))
                        stack.append(len(obj))
                    elif isinstance(pname, compat_str):  # Member access
                        obj = stack.pop()
                        if isinstance(obj, _AVMClass):
                            res = obj.static_properties[pname]
                            stack.append(res)
                            continue

                        assert isinstance(obj, (dict, _ScopeDict)),\
                            'Accessing member %r on %r' % (pname, obj)
                        res = obj.get(pname, undefined)
                        stack.append(res)
                    else:  # Assume attribute access
                        idx = stack.pop()
                        assert isinstance(idx, int)
                        obj = stack.pop()
                        assert isinstance(obj, list)
                        stack.append(obj[idx])
                elif opcode == 104:  # initproperty
                    index = u30()
                    value = stack.pop()
                    idx = self.multinames[index]
                    if isinstance(idx, _Multiname):
                        idx = stack.pop()
                    obj = stack.pop()
                    obj[idx] = value
                elif opcode == 115:  # convert_
                    value = stack.pop()
                    intvalue = int(value)
                    stack.append(intvalue)
                elif opcode == 128:  # coerce
                    u30()
                elif opcode == 130:  # coerce_a
                    value = stack.pop()
                    # um, yes, it's any value
                    stack.append(value)
                elif opcode == 133:  # coerce_s
                    assert isinstance(stack[-1], (type(None), compat_str))
                elif opcode == 147:  # decrement
                    value = stack.pop()
                    assert isinstance(value, int)
                    stack.append(value - 1)
                elif opcode == 149:  # typeof
                    value = stack.pop()
                    return {
                        _Undefined: 'undefined',
                        compat_str: 'String',
                        int: 'Number',
                        float: 'Number',
                    }[type(value)]
                elif opcode == 160:  # add
                    value2 = stack.pop()
                    value1 = stack.pop()
                    res = value1 + value2
                    stack.append(res)
                elif opcode == 161:  # subtract
                    value2 = stack.pop()
                    value1 = stack.pop()
                    res = value1 - value2
                    stack.append(res)
                elif opcode == 162:  # multiply
                    value2 = stack.pop()
                    value1 = stack.pop()
                    res = value1 * value2
                    stack.append(res)
                elif opcode == 164:  # modulo
                    value2 = stack.pop()
                    value1 = stack.pop()
                    res = value1 % value2
                    stack.append(res)
                elif opcode == 168:  # bitand
                    value2 = stack.pop()
                    value1 = stack.pop()
                    assert isinstance(value1, int)
                    assert isinstance(value2, int)
                    res = value1 & value2
                    stack.append(res)
                elif opcode == 171:  # equals
                    value2 = stack.pop()
                    value1 = stack.pop()
                    result = value1 == value2
                    stack.append(result)
                elif opcode == 175:  # greaterequals
                    value2 = stack.pop()
                    value1 = stack.pop()
                    result = value1 >= value2
                    stack.append(result)
                elif opcode == 192:  # increment_i
                    value = stack.pop()
                    assert isinstance(value, int)
                    stack.append(value + 1)
                elif opcode == 208:  # getlocal_0
                    stack.append(registers[0])
                elif opcode == 209:  # getlocal_1
                    stack.append(registers[1])
                elif opcode == 210:  # getlocal_2
                    stack.append(registers[2])
                elif opcode == 211:  # getlocal_3
                    stack.append(registers[3])
                elif opcode == 212:  # setlocal_0
                    registers[0] = stack.pop()
                elif opcode == 213:  # setlocal_1
                    registers[1] = stack.pop()
                elif opcode == 214:  # setlocal_2
                    registers[2] = stack.pop()
                elif opcode == 215:  # setlocal_3
                    registers[3] = stack.pop()
                else:
                    raise NotImplementedError(
                        'Unsupported opcode %d' % opcode)

        avm_class.method_pyfunctions[func_name] = resfunc
        return resfunc
