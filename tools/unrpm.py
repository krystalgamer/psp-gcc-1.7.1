import sys, os, struct, gzip, bz2, lzma, stat
def hdr_len(d, off):
    assert d[off:off+3] == b'\x8e\xad\xe8', hex(off)
    n, sz = struct.unpack('>II', d[off+8:off+16])
    return 16 + n*16 + sz
def payload(path):
    d = open(path, 'rb').read()
    off = 96; off += hdr_len(d, off); off = (off + 7) & ~7
    off += hdr_len(d, off)
    p = d[off:]
    if p[:2] == b'\x1f\x8b': return gzip.decompress(p)
    if p[:3] == b'BZh': return bz2.decompress(p)
    return lzma.decompress(p)
def extract(root, path):
    c = payload(path); i = 0; links = {}
    while True:
        h = c[i:i+110]; assert h[:6] in (b'070701', b'070702'), h[:6]
        f = [int(h[6+8*k:14+8*k], 16) for k in range(13)]
        ino, mode, nlink, fsize, nsz = f[0], f[1], f[4], f[6], f[11]
        name = c[i+110:i+110+nsz-1].decode(); i = (i + 110 + nsz + 3) & ~3
        data = c[i:i+fsize]; i = (i + fsize + 3) & ~3
        if name == 'TRAILER!!!': break
        dst = os.path.join(root, name.lstrip('./'))
        if stat.S_ISDIR(mode): os.makedirs(dst, exist_ok=True); continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.lexists(dst): os.remove(dst)
        if stat.S_ISLNK(mode): os.symlink(data.decode(), dst)
        elif stat.S_ISREG(mode):
            if nlink > 1:
                links.setdefault(ino, []).append(dst)
                if fsize == 0: continue
                for o in links[ino]:
                    if os.path.lexists(o): os.remove(o)
                    open(o, 'wb').write(data); os.chmod(o, (mode & 0o7777) | 0o200)
                continue
            open(dst, 'wb').write(data); os.chmod(dst, (mode & 0o7777) | 0o200)
for p in sys.argv[2:]: extract(sys.argv[1], p)
