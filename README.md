# psp-gcc 1.7.1 reconstruction

This repository rebuilds the source of Sony's PSP compiler
`psp-gcc` 1.7.1 (`gcc version 3.3.3+allegrex-2.2.2-psp-1.7.1`), so it can
be rebuilt and kept running on modern 64-bit hosts. The original release
binaries are 32-bit x86 Linux programs. Reference archive:
<https://github.com/decompme/compilers/releases/download/compilers/psp-gcc-1.7.1.tar.gz>.

Sony never published the patches. `gcc-3.3.3/` starts from pristine FSF
GCC 3.3.3 (tag `fsf-gcc-3.3.3`). The 1.7.1 changes sit on top of the
reconstructed psp-gcc 1.3.1 (tag `psp-1.3.1`; `psp-1.3.1-master` is its
host port). They were reconstructed from the original binaries, which have
symbols, and from the debugging information in the released `libgcc.a`,
`libstdc++.a` and `libsupc++.a`:

- strings, symbols, `insn_data` and the `abort()` line numbers in `cc1`
- emulation of the original `cc1` and decompiled functions
- `DW_AT_decl_line` values and line tables of the libraries
- the installed headers, specs and libraries

The reconstruction was then checked by rebuilding with the original
toolchain (see "Verification"). Binutils are not covered here.

## Branches

- **`sony`**: FSF GCC 3.3.3 plus the reconstructed PSP changes, and nothing
  else. Built on Red Hat Linux 9 with its gcc 3.2.2, as the original was, it
  reproduces the original executables.
- **`master`**: `sony` plus the changes needed to build and run correctly on
  modern and 64-bit hosts, the build script, the tools and this README. It
  produces the same compiler output and libraries as the original.

Patch series:

```sh
git format-patch fsf-gcc-3.3.3..psp-1.3.1 -- gcc-3.3.3  # psp-gcc 1.3.1
git format-patch psp-1.3.1..sony -- gcc-3.3.3           # 1.3.1 -> 1.7.1
git format-patch sony..master -- gcc-3.3.3              # the host/x64 port
```

## Changes

For the 1.3.1 changes (Allegrex support, the `psp` target and thread model,
the driver's SDK handling, Shift-JIS strings, combine and libstdc++
changes, Japanese messages), see the commits up to `psp-1.3.1`.

**1.3.1 to 1.7.1 (`sony`):**

- **Version:** `3.3.3+allegrex-2.2.2-psp-1.7.1`, `__psp_gcc__=0x010701`, specs file `pspspecs_1_7_1`.
- **32-bit host types:** `MAX_LONG_TYPE_SIZE=32` and `MAX_WCHAR_TYPE_SIZE=32` in the psp `tm_defines`, so `HOST_WIDE_INT` and cpplib's `cppchar_t` are 32 bits wide. `c-common.c` and `cp/rtti.c` keep the TImode types.
- **`-mno-ulsw` is no longer the default:** unaligned words use `lwl`/`lwr`/`swl`/`swr`.
- **`mips.md`:**
  - earlyclobber scratches in the double-word patterns
  - `madd`/`msub` with a tied accumulator operand
  - `insv_allegrex` can insert zero
  - `abs` as `max (x, -x)` on Allegrex 3.1
  - `loadgpsym` (`la $28,_gp`)
  - constant rotate counts reduced modulo 32
  - asm statements stay out of delay slots
- **`-mcallee-saved-gp` and the `gp_safe` function attribute:** `$gp` saved and restored like a callee-saved register, reloaded from `_gp`.
- **`gthr-psp.h`:** mutexes lock by suspending interrupts instead of using semaphores; `sceKernelCpuResumeIntr` returns `void` (also in libstdc++'s `atomicity.h`).
- **libgcc** is built with `-g` again.
- **Source layout only** (line numbers in `abort()` calls and debugging information): `cpplex.c`, `block_move_loop_allegrex`, `enum mips_builtins` moved to `mips.h`. Sony's `mips.h` has eleven lines whose content cannot be recovered; a comment of the same length stands in for them.

**Host port (`master`):**

- `include/obstack.h`, `cp/decl.c`: build with current GCC.
- `varasm.c`, `mips.c` (`fmask`), `cp/mangle.c` (ABI-v1 real constants):
  - remove LP64 host dependencies
  - the output is the same as the original i386-hosted compiler's
- `libiberty/stable-qsort.c`, `gcc/system.h`:
  - every `qsort` in GCC uses a merge sort that behaves exactly like the glibc 2.3 `qsort` of the original build host
  - so the output does not depend on the host C library when a comparison returns 0 for different elements
- `ltmain.sh`: deterministic archive member order.
- `gcc/Makefile.in`: fixes a parallel-make race.
- `dwarf2out.c`: attribute values stay 32 bits wide on every host.
- **32-bit `HOST_WIDE_INT` on LP64 hosts** (1.7.1):
  - `hwint.h`: `HOST_WIDE_INT` stays `int`, as on the original i386 host
  - `real.c`, `real.h`: support a 64-bit `long` with it
  - `rtl.h` and users: copy and compare whole operand slots, since an `rtunion` is wider than a `HOST_WIDE_INT`

## Building

```sh
PATH=/path/to/psp-binutils/bin:$PATH ./build-psp-gcc.sh install
```

`build-psp-gcc.sh` configures with the same options as the original and
installs to `PREFIX` (default `/usr/local/psp/gcc-1.7.1`). For details, see
the comments at the top of the script.

Requirements:

- the psp binutils in `PATH`
- the target C library (newlib) headers and libraries in `$PREFIX/psp/include` and `$PREFIX/psp/lib`
- for the same `.eh_frame` flags as the original, the PSP SDK linker scripts in `/usr/local/psp/devkit/lib/ldscripts` (configure checks `psp-ld -shared`)

The 1.7.1 compiler emits `lwl`/`lwr`/`swl`/`swr` by default, and libgcc
uses `ulw`. The 1.3.1 psp binutils reject or expand them differently. If
the 1.7.1 binutils are not available, `tools/as-ulsw.py` can wrap the 1.3.1
`psp-as`.

## Verification

### `sony` on the original toolchain

`tools/rh9-i386-build.sh` builds the `sony` branch the way the original was
built. It needs `bwrap`; no root and no Red Hat installation required.

- **Environment:**
  - Red Hat Linux 9 gcc 3.2.2-5 and binutils 2.13.90.0.18-9
  - glibc 2.3.2-27.9.7 (i686), the version the original was linked against
  - default `-g -O2`, configured from a sibling directory
  - the PSP SDK linker scripts present (`PSP_LDSCRIPTS`)
  - Sony's build directory (`PSP_BUILDDIR`)
  - binaries stripped with `strip -g`, like rpmbuild's `brp-strip`
- **Byte-identical to the original:** `cc1`, `cc1plus`, `collect2`, `psp-gcc`, `psp-c++`, `fixincl` and `fix-header`. (`psp/bin/g++` is an empty file in the release archive.)
- `tools/fcmp.py` compares two executables function by function.

### `master` on a modern x86_64 host

Everything below was compared against the original release. The original
binaries ran under an i386 glibc.

- **`cc1`/`cc1plus` output is byte-identical:**
  - `gcc.c-torture` (1180 files, `-O0`/`-O2`/`-Os`/`-O3 -funroll-loops`)
  - `gcc.dg` (904 files) and `g++.dg` + `g++.old-deja` (3955 files) with 9 more option sets (`-O1`, `-O2` with `-g`, `-mno-ulsw`, `-mcallee-saved-gp`, `-march=allegrex2`/`allegrex3`, `-mext`, ...), and the C++ files again at `-O0`/`-O2`/`-Os`
  - except `g++.dg/abi/mangle13.C`: the original crashes on it (undefined behaviour in GCC's mangler), and this build loops
- **Installed files:** the file list, `crt{begin,end,i,n}.o`, the specs file, the C and C++ headers and the `install-tools` scripts are identical.
- **Libraries:** `libgcc.a`, `libstdc++.a` and `libsupc++.a` are identical member by member, debugging information included (built with Sony's prefix and build directory; `tools/libcmp.py`). The exceptions all come from Sony's build environment:
  - **Random names:** four members (`ext-inst.o`, `io-inst.o`, `locale-inst.o`, `vec.o`) contain random six-character suffixes, which GCC derives from the time and pid of each compile. Compiled with the `-frandom-seed` that `tools/seed4suffix.py` finds for the original suffix, they are identical too.
  - **ar headers:** the member dates, uid and gid. With those taken from the original, and the symbol index carrying the original random names, all three archives are byte-identical.
  - **`libstdc++.la`/`libsupc++.la`:** the library search paths Sony's driver used. The original build ran with `SCE_PSP_SDK_HOME=/` (hence `-L//lib`) and with an existing `/usr/local/psp/gcc-1.7.1` installation.
  - **`mkheaders.conf`:** records the RPM build root, `/var/tmp/psp-gcc_1_7_1-1.7.1-root`.
