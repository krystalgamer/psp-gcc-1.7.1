#!/usr/bin/env python3
"""Test-only psp-as wrapper (usage: as-ulsw.py [psp-as arguments]).

The 1.3.1 psp assembler rejects lwl/lwr/swl/swr for Allegrex and expands
the ulw/usw macros into byte sequences, while the 1.7.1 assembler (not
available) accepts them and expands ulw/usw into lwl/lwr and swl/swr
pairs.  Emulate that: assemble each such instruction as a same-format
placeholder (ll, ldc2, sc, sdc2) so that gas still treats it as an
instruction (line table rows, alignment), then patch the opcode field in
the object's executable sections.  Install it as psp-as ahead of the real
one in PATH and set ULSW_REAL_AS to the real assembler command."""
import sys, os, re, shlex, struct, subprocess, tempfile
if not os.environ.get('ULSW_REAL_AS'):
    sys.exit('as-ulsw: set ULSW_REAL_AS to the real (1.3.1) psp-as command')
REAL = shlex.split(os.environ['ULSW_REAL_AS'])
PH = {'lwl': 'll', 'lwr': 'ldc2', 'swl': 'sc', 'swr': 'sdc2'}
FIX = {0x30: 0x22, 0x36: 0x26, 0x38: 0x2a, 0x3e: 0x2e}
NAMES = {'zero': 0, 'gp': 28, 'sp': 29, 'fp': 30, 'ra': 31, 'at': 1}
def reg(r):
    r = r.strip().lstrip('$')
    return int(r) if r.isdigit() else NAMES[r]
PAT = re.compile(r'^(\s*)(lwl|lwr|swl|swr|ulw|usw)\s+(\$\w+)\s*,\s*(-?\d+)\((\$\w+)\)\s*$')
count = 0
def conv(line):
    global count
    m = PAT.match(line)
    if not m: return line
    ind, op, rt, off, base = m.group(1), m.group(2), reg(m.group(3)), int(m.group(4)), reg(m.group(5))
    if op in ('ulw', 'usw'):
        hi, lo = ('lwl', 'lwr') if op == 'ulw' else ('swl', 'swr')
        t = 1 if (op == 'ulw' and rt == base) else rt
        out = ['%s\t$%d,%d($%d)' % (PH[hi], t, off + 3, base), '%s\t$%d,%d($%d)' % (PH[lo], t, off, base)]
        if t != rt: out.append('move\t$%d,$1' % rt)
    else:
        out = ['%s\t$%d,%d($%d)' % (PH[op], rt, off, base)]
    count += sum(1 for o in out if not o.startswith('move'))
    return ''.join('%s%s\t# %s\n' % (ind, o, line.strip()) for o in out)
def patch(obj, expect):
    d = bytearray(open(obj, 'rb').read())
    shoff, = struct.unpack_from('<I', d, 0x20); shentsize, shnum = struct.unpack_from('<HH', d, 0x2e)
    n = 0
    for i in range(shnum):
        _, typ, flags, _, off, size = struct.unpack_from('<IIIIII', d, shoff + i * shentsize)
        if typ != 1 or not flags & 4: continue
        for p in range(off, off + size - 3, 4):
            w, = struct.unpack_from('<I', d, p)
            if w >> 26 in FIX:
                struct.pack_into('<I', d, p, FIX[w >> 26] << 26 | (w & 0x3ffffff)); n += 1
    if n != expect:
        sys.exit('as-ulsw: patched %d words, expected %d' % (n, expect))
    open(obj, 'wb').write(d)
args = sys.argv[1:]
srcs = [i for i, a in enumerate(args) if a.endswith('.s') or a == '-']
tmp = None
if srcs:
    i = srcs[-1]
    data = sys.stdin.read() if args[i] == '-' else open(args[i]).read()
    if re.search(r'^\s*(ll|sc|ldc2|sdc2)\s', data, re.M):
        sys.exit('as-ulsw: input already uses a placeholder opcode')
    fd, tmp = tempfile.mkstemp(suffix='.s'); os.close(fd)
    open(tmp, 'w').write(''.join(conv(l) for l in data.splitlines(True)))
    args[i] = tmp
r = subprocess.call(REAL + args)
if tmp: os.unlink(tmp)
if r == 0 and count:
    out = args[args.index('-o') + 1] if '-o' in args else 'a.out'
    patch(out, count)
sys.exit(r)
