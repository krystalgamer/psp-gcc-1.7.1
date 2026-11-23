#!/bin/sh
# Build the reconstructed psp-gcc 1.3.1 (GCC 3.3.3+allegrex-2.2.1-psp-1.3.1)
# on a modern 64-bit Linux host.
#
# Usage: ./build-psp-gcc.sh [build|install]
#
# Environment:
#   PREFIX  installation prefix (default /usr/local/psp/gcc-1.3.1)
#   BUILD   build directory     (default ./build, next to gcc-3.3.3 so that
#           paths embedded in the libraries match the original build)
#   JOBS    parallel make jobs  (default 4)
#   CC      host C compiler     (default gcc)
#
# Requirements:
#   - psp binutils (psp-as, psp-ld, psp-ar, psp-ranlib, psp-nm, ...) in PATH
#   - the target C library headers and libraries (newlib from the PSP
#     toolchain) in $PREFIX/psp/include and $PREFIX/psp/lib; libstdc++
#     cannot be configured without them.

set -e

TOP=$(cd "$(dirname "$0")" && pwd)
PREFIX=${PREFIX:-/usr/local/psp/gcc-1.3.1}
BUILD=${BUILD:-$TOP/build}
JOBS=${JOBS:-4}
STEP=${1:-build}

# GCC 3.3 is old K&R-ish C; let a modern host compiler accept it.
HOST_CC="${CC:-gcc} -std=gnu89 -fcommon -w -fpermissive"
HOST_CC="$HOST_CC -Wno-error=implicit-function-declaration -Wno-error=implicit-int"
HOST_CC="$HOST_CC -Wno-error=int-conversion -Wno-error=incompatible-pointer-types"

# Without the PSP SDK, <kernel.h> is not available; _IN_GCC_LIB makes
# gthr-psp.h use its own declarations (the libraries themselves are
# already built with it through --enable-cxx-flags).
CXXFLAGS_FOR_TARGET="-g -O2 -D_IN_GCC_LIB"

for tool in psp-as psp-ld psp-ar psp-ranlib; do
  command -v $tool >/dev/null 2>&1 || {
    echo "error: $tool not found in PATH" >&2; exit 1; }
done
if [ ! -f "$PREFIX/psp/include/stdio.h" ]; then
  echo "error: target C library headers not found in $PREFIX/psp/include" >&2
  exit 1
fi

mkdir -p "$BUILD"
cd "$BUILD"
if [ ! -f config.status ]; then
  # Configure with a relative path when the build directory is a sibling
  # of the source tree, as the original was.
  if [ "$(cd .. && pwd)" = "$TOP" ]; then
    SRC=../gcc-3.3.3
  else
    SRC=$TOP/gcc-3.3.3
  fi
  CC="$HOST_CC" $SRC/configure --target=psp --prefix="$PREFIX" \
    --with-gnu-ld --with-gnu-as --enable-languages=c,c++ \
    --enable-c-mbchar --enable-threads=psp --enable-cxx-flags=-D_IN_GCC_LIB
fi

make -j"$JOBS" all-gcc
make -j"$JOBS" all-target-libstdc++-v3 CXXFLAGS_FOR_TARGET="$CXXFLAGS_FOR_TARGET"

if [ "$STEP" = install ]; then
  make install-gcc
  make install-target-libstdc++-v3 CXXFLAGS_FOR_TARGET="$CXXFLAGS_FOR_TARGET"
fi
