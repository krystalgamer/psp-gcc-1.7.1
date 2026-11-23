#!/usr/bin/env python3
"""Compare functions of two i386 ELF executables by symbol.
Code is compared after resolving absolute addresses / call targets to
symbol+offset, so that layout shifts do not count as differences."""
import sys, bisect, capstone
from elftools.elf.elffile import ELFFile
from capstone import x86

def load(path):
    e = ELFFile(open(path, 'rb'))
    secs = [(s['sh_addr'], s['sh_addr'] + s['sh_size'], s) for s in e.iter_sections() if s['sh_addr']]
    syms = {}
    allsyms = []
    for s in e.get_section_by_name('.symtab').iter_symbols():
        if s['st_shndx'] in ('SHN_UNDEF', 'SHN_ABS') or not s.name: continue
        allsyms.append((s['st_value'], s.name))
        if s['st_info']['type'] == 'STT_FUNC':
            key = s.name
            if s['st_info']['bind'] == 'STB_LOCAL':
                key = s.name  # locals may collide; keep first-come with suffix
                k = 1
                while key in syms: k += 1; key = '%s#%d' % (s.name, k)
            syms[key] = (s['st_value'], s['st_size'])
    allsyms.sort()
    text = e.get_section_by_name('.text')
    return dict(e=e, syms=syms, addrs=[a for a, _ in allsyms], names=[n for _, n in allsyms],
                tbase=text['sh_addr'], tdata=text.data(), secs=secs,
                plt=e.get_section_by_name('.plt'))

def sym_of(img, v):
    for lo, hi, sec in img['secs']:
        if lo <= v < hi and sec.name in ('.rodata', '.eh_frame', '.comment'):
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
