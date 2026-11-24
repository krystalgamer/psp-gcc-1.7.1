#!/bin/sh
# Build gcc-3.3.3 the way the original psp-gcc was built: on Red Hat
# Linux 9 (i386) with its gcc 3.2.2-5, binutils 2.13.90.0.18-9 and glibc
# 2.3.2-27.9.7 (i686), then strip -g like rpmbuild's brp-strip.  With the
# "sony" branch checked out, cc1/cc1plus/cpp/xgcc/g++/collect2 can then be
# compared with the original binaries.
#
# Needs: bwrap (bubblewrap) with user namespaces, setarch, python3, curl,
# make and a POSIX shell on the host, and the psp binutils (for libgcc).
#
# Usage: [PSP_VERSION=1.7.1] [PSP_LDSCRIPTS=DIR] \
#        tools/rh9-i386-build.sh WORKDIR PSP_BINUTILS_PREFIX
#   WORKDIR              scratch directory (RPMs, sandbox root, build)
#   PSP_BINUTILS_PREFIX  psp binutils installation: bin/psp-{as,ld,ar,...}
#                        and psp/bin/{as,ld,...}
#
#   PSP_VERSION          release whose prefix (/usr/local/psp/gcc-VERSION) is
#                        used; default 1.7.1
#   PSP_LDSCRIPTS        if set, mounted as the PSP SDK's lib/ldscripts, where
#                        the psp linker looks for its scripts.  Needed for
#                        1.7.1, whose build host had the SDK installed: with
#                        a working "psp-ld -shared", configure defines
#                        HAVE_LD_RO_RW_SECTION_MIXING.
#   PSP_BUILDDIR         if set, the build directory is mounted at this path
#                        (with gcc-3.3.3 next to it), so that the paths in
#                        the libgcc debugging information match.  1.7.1 was
#                        built in /home/tei/psp/gcc/pspgcc-1.7.1.release/
#                        rpmwork/BUILD/psp-gcc_1_7_1-1/workforbuild/gcc-bin.
#
# The binaries end up in WORKDIR/stripped.

set -e
V=${PSP_VERSION:-1.7.1}
TOOLS=$(cd "$(dirname "$0")" && pwd)
TOP=${TOP:-$(cd "$(dirname "$0")/.." && pwd)}
W=$(mkdir -p "$1" && cd "$1" && pwd)
B=$(cd "$2" && pwd)
M=https://mirror.math.princeton.edu/pub/redhat-archive/redhat/linux
GA=$M/9/en/os/i386/RedHat/RPMS
UPD=$M/updates/9/en/os

mkdir -p "$W/rpms"
cd "$W/rpms"
for p in $GA/binutils-2.13.90.0.18-9.i386.rpm $GA/cpp-3.2.2-5.i386.rpm \
	 $GA/gcc-3.2.2-5.i386.rpm $GA/libgcc-3.2.2-5.i386.rpm \
	 $GA/glibc-kernheaders-2.4-8.10.i386.rpm \
	 $UPD/i386/glibc-common-2.3.2-27.9.7.i386.rpm \
	 $UPD/i686/glibc-2.3.2-27.9.7.i686.rpm \
	 $UPD/i386/glibc-devel-2.3.2-27.9.7.i386.rpm; do
  [ -f "$(basename $p)" ] || curl -sfLO "$p"
done

# Sandbox root: RH9 /usr/include, and a /usr/lib that holds the RH9 libraries
# and compiler next to symlinks to the host's /usr/lib entries (the host's
# /usr/lib is bound to /tmp/.rh9hostlib inside the sandbox).
rm -rf "$W/root" "$W/lib"
python3 "$TOOLS/unrpm.py" "$W/root" "$W"/rpms/*.rpm
mkdir "$W/lib"
cp -a "$W/root/usr/lib/." "$W/lib/"
find "$W/root/lib" -maxdepth 1 \( -type f -o -type l \) -exec cp -a {} "$W/lib/" \;
for e in /usr/lib/* /usr/lib/.[!.]*; do
  [ -e "$e" ] || [ -L "$e" ] || continue
  n=$(basename "$e")
  [ -e "$W/lib/$n" ] || [ -L "$W/lib/$n" ] || ln -s "/tmp/.rh9hostlib/$n" "$W/lib/$n"
done
for l in $(find "$W/lib" -maxdepth 1 -type l); do
  case $(readlink "$l") in
    ../../lib/*|/lib/*) ln -sfn "$(basename "$(readlink "$l")")" "$l" ;;
  esac
done
G=$W/lib/gcc-lib/i386-redhat-linux/3.2.2
ln -sfn "$W/root/usr/bin/as" "$G/as"
ln -sfn "$W/root/usr/bin/ld" "$G/ld"

BD=$W/src/gcc-bin
EXTRA=
if [ -n "$PSP_BUILDDIR" ]; then
  BD=$PSP_BUILDDIR
  EXTRA="--tmpfs /home --bind $HOME $HOME --bind $W/src $(dirname "$PSP_BUILDDIR")"
fi

run () {
  bwrap --dev-bind / / $EXTRA \
    --ro-bind /usr/lib /tmp/.rh9hostlib \
    --ro-bind "$W/lib" /usr/lib \
    --ro-bind "$W/root/usr/include" /usr/include \
    --tmpfs /usr/local \
    --ro-bind "$B/psp" /usr/local/psp/gcc-$V/psp \
    ${PSP_LDSCRIPTS:+--ro-bind "$PSP_LDSCRIPTS" /usr/local/psp/devkit/lib/ldscripts} \
    --setenv PATH "$W/root/usr/bin:/usr/bin:/bin" \
    --setenv LC_ALL C \
    setarch i686 "$@"
}

# The original was configured from a sibling directory of gcc-3.3.3.
rm -rf "$W/src" && mkdir -p "$W/src/gcc-bin"
ln -s "$TOP/gcc-3.3.3" "$W/src/gcc-3.3.3"
run sh -c "cd $BD && PATH=$B/bin:\$PATH; export PATH;
  ../gcc-3.3.3/configure --target=psp \
  --prefix=/usr/local/psp/gcc-$V --with-gnu-ld --with-gnu-as \
  --enable-languages=c,c++ --enable-c-mbchar --enable-threads=psp \
  --enable-cxx-flags=-D_IN_GCC_LIB > configure.log 2>&1 &&
  make all-gcc > make.log 2>&1"

mkdir -p "$W/stripped"
for f in cc1 cc1plus cpp xgcc g++ collect2; do
  run strip -g -o "$W/stripped/$f" "$W/src/gcc-bin/gcc/$f"
done
echo "Stripped binaries are in $W/stripped"
