"""
bfc.py -- a Brainfuck compiler that targets yt-dlp's jsinterp.

This is the proof object for the "Shifting the Trap" / "Compiling the Trap"
argument. It does *not* import or depend on yt-dlp. It takes a Brainfuck
program and emits a single JavaScript function as a source string.

That string is written against the *intersection* of JavaScript and the
subset that yt_dlp/jsinterp.py actually implements -- and, deliberately,
against the smaller intersection that the much older yt-dlp 2022.04.08
also accepts. We use:

  * `for (; truthy_value; ) { ... }`  -- the only loop construct, and the
    only loop guard, that has existed across the range. The 2022.04.08
    interpreter has *no* comparison operators (`==`, `!=`, `<`, `>`) at
    all, and no `if`/`else` or ternary, so guards must be a single value
    tested for truthiness.
  * arrays with `.push`, `t[i]`, `t[i] = expr`, `.length`, `.join`
  * 32-bit integer/bitwise ops (`& 255` gives Brainfuck's mod-256 cells,
    including correct wrap on `(0 - 1) & 255 == 255`)
  * `String.fromCharCode(...)` for output; the output is collected into
    an array and `.join("")`ed at the end, because old jsinterp did not
    implement string concatenation with `+`.

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

Empirically verified against:
  * yt_dlp.jsinterp on this branch (current)
  * yt-dlp 2022.04.08 (the version Jacob K used in his original forum post)
"""

from __future__ import annotations

# Brainfuck command -> JavaScript statement(s). The choices here are all
# constrained by what 2022.04.08 jsinterp accepts:
#
#   - loop guards must be a single value (truthiness), not a comparison;
#     `[ ]` lowers to `for(;t[p];){...}`.
#   - cell math is masked with `& 255`; jsinterp's bit ops use Python's
#     `&`, so `(t[p] - 1) & 255` wraps 0 -> 255 exactly like Brainfuck.
#   - the input read for `,` is *unguarded*: old jsinterp has no if/else
#     or ternary, so we trust the caller to supply enough input bytes.
#     (None of the proof programs ever over-read.)
_IO = {
    '.': 'o.push(String.fromCharCode(t[p]));',
    ',': 't[p]=inp[ip];ip=ip+1;',
    '[': 'for(;t[p];){',
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
    values consumed by the `,` command.
    """
    body = list(_emit_runs(src))

    # Build the tape with a countdown loop, because old jsinterp has no
    # comparison operators with which to write an `i < N` guard.
    prologue = (
        f'var t=[];var p=0;var o=[];var ip=0;var i={int(tape_size)};'
        f'for(;i;i=i-1){{t.push(0)}}'
    )
    return (
        f'function {func_name}(inp){{'
        f'{prologue}'
        f'{"".join(body)}'
        f'return o.join("")'
        f'}}'
    )


if __name__ == '__main__':
    import sys
    data = sys.stdin.read()
    sys.stdout.write(compile_bf(data))
