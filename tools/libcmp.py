#!/usr/bin/env python3
"""libcmp.py ORIG.a NEW.a: compare two ar archives member by member.

Each member is reported as identical, as differing only in the random
six-character suffixes GCC 3.3 appends to the names of global
constructors/destructors and anonymous namespaces (seeded from the time
and pid of each compilation), or as different.  With debugging
information the order of .debug_str also follows those names, so such
members are listed with the -frandom-seed that reproduces the original
names; rebuild them with it to compare.  Differences in the ar member
headers (date, uid, gid, mode) are summarised separately."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib
seed4suffix = importlib.import_module('seed4suffix')

def members(path):
    d = open(path, 'rb').read()
    assert d[:8] == b'!<arch>\n', path
    p, out, names = 8, [], b''
    while p < len(d):
        h = d[p:p + 60]
        name, date, uid, gid, mode, size = (h[0:16], h[16:28], h[28:34], h[34:40], h[40:48], h[48:58])
        size = int(size)
        body = d[p + 60:p + 60 + size]
        n = name.rstrip(b' ')
        if n == b'//':
            names = body
        elif n != b'/':
            if n.startswith(b'/'):
                off = int(n[1:]); n = names[off:names.index(b'\n', off)]
            out.append((n.rstrip(b'/').decode(), body, (date.strip(), uid.strip(), gid.strip(), mode.strip())))
        p += 60 + size + (size & 1)
    return out

SUFFIX = re.compile(rb'(_GLOBAL__[IDN]_[\x21-\x7e]*?\.(?:cc|c|C|cpp|cxx))([A-Za-z0-9]{6})')

def normalize(a, b):
    sa = [m.group(2) for m in SUFFIX.finditer(a)]
    sb = [m.group(2) for m in SUFFIX.finditer(b)]
    for x, y in set(zip(sa, sb)):
        a = a.replace(x, y)
    return a

def main(orig, new):
    A, B = members(orig), members(new)
    if [m[0] for m in A] != [m[0] for m in B]:
        print('MEMBER LIST DIFFERS'); return 1
    same = rnd = 0; bad = []; seeds = []; hdr = set()
    for (n, a, ha), (_, b, hb) in zip(A, B):
        for f, x, y in zip(('date', 'uid', 'gid', 'mode'), ha, hb):
            if x != y: hdr.add(f)
        sa = sorted(set(m.group(2) for m in SUFFIX.finditer(a)))
        sb = sorted(set(m.group(2) for m in SUFFIX.finditer(b)))
        if a == b: same += 1
        elif len(a) == len(b) and normalize(a, b) == b: rnd += 1
        elif len(sa) == 1 and sa != sb:
            seeds.append((n, sa[0].decode()))
        else: bad.append(n)
    print('%d members: %d identical, %d differ only in random name suffixes, %d different%s'
          % (len(A), same, rnd, len(bad) + len(seeds), (': ' + ' '.join(bad)) if bad else ''))
    for n, sfx in seeds:
        print('  %s: random names differ (original %s; compile with -frandom-seed=%s)'
              % (n, sfx, seed4suffix.find(sfx)))
    if hdr:
        print('ar header fields that differ: ' + ', '.join(sorted(hdr)))
    return 1 if bad or seeds else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
