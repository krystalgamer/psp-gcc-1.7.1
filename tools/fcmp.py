#!/usr/bin/env python3
"""Compare functions of two i386 ELF executables by symbol.
Code is compared after resolving absolute addresses / call targets to
symbol+offset, so that layout shifts do not count as differences.
With FCMP_CONTENT=1, references into .rodata are compared by what they
point to (the object or string there) rather than by offset."""
import sys, bisect, capstone
from elftools.elf.elffile import ELFFile
from capstone import x86

def load(path):
    e = ELFFile(open(path, 'rb'))
    secs = [(s['sh_addr'], s['sh_addr'] + s['sh_size'], s) for s in e.iter_sections() if s['sh_addr']]
    syms = {}
    allsyms = []
    objsize = {}
    for s in e.get_section_by_name('.symtab').iter_symbols():
        if s['st_shndx'] in ('SHN_UNDEF', 'SHN_ABS') or not s.name: continue
        allsyms.append((s['st_value'], s.name))
        if s['st_info']['type'] == 'STT_OBJECT': objsize[s['st_value']] = s['st_size']
        if s['st_info']['type'] == 'STT_FUNC':
            key = s.name
            if s['st_info']['bind'] == 'STB_LOCAL':
                key = s.name  # locals may collide; keep first-come with suffix
                k = 1
                while key in syms: k += 1; key = '%s#%d' % (s.name, k)
            syms[key] = (s['st_value'], s['st_size'])
    allsyms.sort()
    text = e.get_section_by_name('.text')
    return dict(objsize=objsize, e=e, syms=syms, addrs=[a for a, _ in allsyms], names=[n for _, n in allsyms],
                tbase=text['sh_addr'], tdata=text.data(), secs=secs,
                plt=e.get_section_by_name('.plt'))

import os, hashlib
CONTENT = os.environ.get('FCMP_CONTENT')

def ro_sig(img, sec, off):
    import struct
    k = bisect.bisect_right(img['addrs'], sec['sh_addr'] + off) - 1
    if k >= 0 and img['addrs'][k] == sec['sh_addr'] + off and not img['names'][k].startswith('.'):
        return img['names'][k]
    if k >= 0 and not img['names'][k].startswith('.') and img['objsize'].get(img['addrs'][k], 0) > sec['sh_addr'] + off - img['addrs'][k]:
        return '%s+%d' % (img['names'][k], sec['sh_addr'] + off - img['addrs'][k])
    d = sec.data()
    s = d[off:off + 64]
    if s[:1] not in (b'', b'\0') and b'\0' in s and all(32 <= c < 127 or c in (9, 10) for c in s.split(b'\0')[0]):
        return hashlib.md5(s.split(b'\0')[0]).hexdigest()[:8]
    parts = []
    for i in range(0, 32, 4):
        if off + i + 4 > len(d): break
        w = struct.unpack_from('<I', d, off + i)[0]
        if 0x8048000 <= w < 0x9000000:
            in_ro = sec['sh_addr'] <= w < sec['sh_addr'] + sec['sh_size']
            parts.append('R' if in_ro else sym_of_plain(img, w))
        else: parts.append(str(w))
    return hashlib.md5(','.join(parts).encode()).hexdigest()[:8]

def sym_of_plain(img, v):
    k = bisect.bisect_right(img['addrs'], v) - 1
    if k < 0: return hex(v)
    a, n = img['addrs'][k], img['names'][k]
    return '%s+%d' % (n, v - a) if v != a else n

def sym_of(img, v):
    for lo, hi, sec in img['secs']:
        if lo <= v < hi and sec.name in ('.rodata', '.eh_frame', '.comment'):
            if CONTENT and sec.name == '.rodata':
                return 'ro:' + ro_sig(img, sec, v - lo)
            return '%s+%d' % (sec.name, v - lo)
    k = bisect.bisect_right(img['addrs'], v) - 1
    if k < 0: return hex(v)
    a, n = img['addrs'][k], img['names'][k]
    if v - a > 0x100000: return hex(v)
    return '%s+%d' % (n, v - a) if v != a else n

def norm(img, name):
    a, sz = img['syms'][name]
    data = img['tdata'][a - img['tbase']: a - img['tbase'] + sz]
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail = True
    out = []
    for ins in md.disasm(data, a):
        ops = ins.op_str
        if (ins.group(x86.X86_GRP_JUMP) or ins.group(x86.X86_GRP_CALL)) and ins.operands and ins.operands[0].type == x86.X86_OP_IMM:
            if True:
                t = ins.operands[0].imm
                ops = ('L%d' % (t - a)) if a <= t < a + sz else sym_of(img, t)
        else:
            for op in ins.operands:
                v = None
                if op.type == x86.X86_OP_IMM: v = op.imm & 0xffffffff
                elif op.type == x86.X86_OP_MEM:
                    v = op.mem.disp & 0xffffffff
                if v is not None and v >= 0x8048000 and v < 0x9000000:
                    ops = ops.replace(hex(v), '<%s>' % sym_of(img, v))
        out.append('%s %s' % (ins.mnemonic, ops))
    return out

if __name__ == '__main__':
    A, B = load(sys.argv[1]), load(sys.argv[2])
    only_a = sorted(set(A['syms']) - set(B['syms'])); only_b = sorted(set(B['syms']) - set(A['syms']))
    same = sizediff = codediff = 0; bad = []
    for n in sorted(set(A['syms']) & set(B['syms'])):
        sa, sb = A['syms'][n][1], B['syms'][n][1]
        if sa != sb: sizediff += 1; bad.append((n, sa, sb, 'size')); continue
        if norm(A, n) != norm(B, n): codediff += 1; bad.append((n, sa, sb, 'code')); continue
        same += 1
    print('same', same, 'size-diff', sizediff, 'code-diff', codediff, 'only-orig', len(only_a), 'only-new', len(only_b))
    print('only-orig:', ' '.join(only_a)); print('only-new:', ' '.join(only_b))
    for b in bad: print('%-40s %6d %6d %s' % b)
