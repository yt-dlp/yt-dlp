"""
bfc.py -- a Brainfuck compiler that targets yt-dlp's jsinterp.

This is the proof object for the "Shifting the Trap" / "Compiling the Trap"
argument. It does *not* import or depend on yt-dlp. It takes a Brainfuck
program and emits a single JavaScript function as a source string.

That string is written against the *intersection* of JavaScript and the
subset that yt_dlp/jsinterp.py actually implements:

  * `for (; cond; ) { ... }`  -- jsinterp has no `while`; Brainfuck `[ ]`
    loops lower to `for` loops whose body re-checks the current cell.
  * arrays with `.push`, `t[i]`, `t[i] = expr`, `.length`
  * 32-bit integer/bitwise ops (`& 255` gives Brainfuck's mod-256 cells,
    including correct wrap on `(0 - 1) & 255 == 255`)
  * `String.fromCharCode(...)` and string `+` for output
  * the ternary operator for `,` (input)

Nothing here uses recursion: Brainfuck loops become JavaScript loops, so
the proof never touches jsinterp's ~100-deep recursion budget. The only
finite resources consumed are the (configurable) tape and the host's
patience -- the same "real machines are finite" footnote that applies to
every physical computer.

The reduction:

    Brainfuck is Turing-complete. `compile_bf` is a total function from
    Brainfuck source to a program jsinterp executes with identical
    observable output. Therefore jsinterp computes every Turing-computable
    function (modulo finite resources). QED.
"""

from __future__ import annotations

# Brainfuck command -> JavaScript statement(s). `{TAPE}` is substituted with
# the tape size. Note the deliberate choices that keep us inside jsinterp's
# real grammar:
#   - loop guard uses loose `!=` (jsinterp's _js_eq_op path), NOT `!==`
#     (Python `is`-identity), so the guard is robust for all cell values.
#   - cell math is masked with `& 255`; jsinterp's _js_bit_op uses Python's
#     `&`, so `(t[p] - 1) & 255` wraps 0 -> 255 exactly like Brainfuck.
#   - pointer moves are explicit `p = p + 1` rather than `p++` to stay on
#     the most boring, most-exercised path through the interpreter.
_IO = {
    '.': 'o=o+String.fromCharCode(t[p]);',
    ',': 't[p]=(ip<inp.length?inp[ip]:0);ip=ip+1;',
    '[': 'for(;t[p]!=0;){',
    ']': '}',
}


def _emit_runs(src: str):
    """Lower Brainfuck to JS, coalescing runs of `+`/`-` into one cell
    assignment and runs of `>`/`<` into one pointer move.

    This is the textbook Brainfuck run-length optimization: `+++` and
    `+ + +` are observationally identical, so collapsing them changes
    nothing about semantics -- it only spares jsinterp's regex walker
    from re-parsing thousands of one-character statements. Loops and I/O
    are still one statement each, exactly as written.
    """
    val = 0   # pending net change to the current cell
    ptr = 0   # pending net pointer move

    def flush_val():
        nonlocal val
        if val:
            yield (f't[p]=(t[p]+{val})&255;' if val > 0
                   else f't[p]=(t[p]-{-val})&255;')
            val = 0

    def flush_ptr():
        nonlocal ptr
        if ptr:
            yield (f'p=p+{ptr};' if ptr > 0 else f'p=p-{-ptr};')
            ptr = 0

    depth = 0
    for ch in src:
        if ch in '+-':
            yield from flush_ptr()
            val += 1 if ch == '+' else -1
        elif ch in '><':
            yield from flush_val()
            ptr += 1 if ch == '>' else -1
        elif ch in _IO:
            yield from flush_val()
            yield from flush_ptr()
            if ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
                if depth < 0:
                    raise ValueError("unbalanced ']' in Brainfuck source")
            yield _IO[ch]
        # every other character is a Brainfuck comment
    yield from flush_val()
    yield from flush_ptr()
    if depth != 0:
        raise ValueError("unbalanced '[' in Brainfuck source")


def compile_bf(src: str, *, tape_size: int = 4096, func_name: str = 'run') -> str:
    """Compile Brainfuck `src` to a jsinterp-compatible JS function string.

    The emitted function has signature `function run(inp) { ... }` and
    returns the program's output as a string. `inp` is an array of byte
    values consumed by the `,` command (0 once exhausted).
    """
    body = list(_emit_runs(src))

    prologue = (
        f'var t=[];var p=0;var o="";var ip=0;var i=0;'
        f'for(i=0;i<{int(tape_size)};i=i+1){{t.push(0)}}'
    )
    return (
        f'function {func_name}(inp){{'
        f'{prologue}'
        f'{"".join(body)}'
        f'return o'
        f'}}'
    )


if __name__ == '__main__':
    import sys
    data = sys.stdin.read()
    sys.stdout.write(compile_bf(data))
