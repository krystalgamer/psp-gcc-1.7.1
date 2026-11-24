#!/usr/bin/env python3
"""seed4suffix.py SUFFIX: print a -frandom-seed value for which GCC 3.3 (with a
32-bit HOST_WIDE_INT, as in psp-gcc 1.7.1) appends SUFFIX to the names of
global constructors/destructors and anonymous namespaces.

GCC derives the six characters from a 32-bit hash of the seed string:
v = rotl(v, 4) ^ c for each character c, written in base 62.  The released
libraries were built without -frandom-seed, so each compilation took its
seed from the time and pid; this recovers an equivalent seed."""
import sys

LETTERS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

def rotl(x, n):
    n %= 32
    return ((x << n) | (x >> (32 - n))) & 0xffffffff if n else x

def gcc_hash(s):
    v = 0
    for c in s.encode():
        v = ((v << 4) ^ (v >> 28) ^ c) & 0xffffffff
    return v

def suffix(v):
    out = ''
    for _ in range(6):
        out += LETTERS[v % 62]; v //= 62
    return out

def solve(target, n=10):
    # Characters 0x40 | b (b: 6 free bits); solve the XOR system over GF(2).
    base = 0
    for i in range(n):
        base ^= rotl(0x40, 4 * (n - 1 - i))
    cols = [rotl(1 << j, 4 * (n - 1 - i)) for i in range(n) for j in range(6)]
    want = target ^ base
    rows, piv = [], []
    for k, c in enumerate(cols):
        vec, comb = c, 1 << k
        for r, (rv, rc) in enumerate(rows):
            if vec & (1 << piv[r]): vec ^= rv; comb ^= rc
        if vec:
            p = vec.bit_length() - 1
            for r in range(len(rows)):
                if rows[r][0] & (1 << p): rows[r] = (rows[r][0] ^ vec, rows[r][1] ^ comb)
            rows.append((vec, comb)); piv.append(p)
    comb = 0
    for (rv, rc), p in zip(rows, piv):
        if want & (1 << p): want ^= rv; comb ^= rc
    if want:
        return None
    bits = [(comb >> k) & 1 for k in range(len(cols))]
    s = ''.join(chr(0x40 | sum(bits[i * 6 + j] << j for j in range(6))) for i in range(n))
    return s if all(0x40 <= ord(ch) < 0x7f for ch in s) else None

def find(sfx):
    v = 0
    for ch in reversed(sfx):
        v = v * 62 + LETTERS.index(ch)
    for n in range(8, 16):
        s = solve(v, n)
        if s and suffix(gcc_hash(s)) == sfx:
            return s
    return None

def main(sfx):
    s = find(sfx)
    if s is None:
        sys.exit('no seed found')
    print(s)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
