# psp-gcc 1.3.1 reconstruction

This repository rebuilds the source of Sony's PSP compiler
`psp-gcc` 1.3.1 (`gcc version 3.3.3+allegrex-2.2.1-psp-1.3.1`), so it can
be rebuilt and kept running on modern 64-bit hosts. The original release
binaries are 32-bit x86 Linux programs. Reference archive:
<https://github.com/decompme/compilers/releases/download/compilers/psp-gcc-1.3.1.tar.gz>.

Sony never published the patches. `gcc-3.3.3/` starts from pristine FSF
GCC 3.3.3 (tag `fsf-gcc-3.3.3`). The changes on top were reconstructed from
the original binaries, which have symbols:

- strings and symbols
- `insn_data`
- emulation of the original `cc1`'s expanders, attributes, costs and
  optab conditions
- decompiled functions
- the installed headers, specs, libraries and message catalogs

Binutils are not covered here.

## Changes

Get the patch series with `git format-patch fsf-gcc-3.3.3..HEAD -- gcc-3.3.3`.

**PSP changes (reconstructed):**

- **Allegrex processor support (`config/mips/mips.{h,c,md}`, `mips-protos.h`):**
  - `-march=allegrex{,2,3,31}`
  - `-m[no-]ulsw`, `-m[no-]ext`, `-m[no-]madd`
  - Allegrex instructions: `clz`/`clo`, `seb`/`seh`, `bitrev`, `wsbh`/`wsbw`, `ext`/`ins`, `min`/`max`, `movz`/`movn`, `rotr`, `madd`/`msub`, and the FP rounding conversions
  - `__builtin_allegrex_*` builtins
  - function units and costs
  - block move strategy
  - 16-byte stack alignment for Allegrex 3.1
- **Target configuration:** `config.gcc`, `config.sub`, `config/mips/psp.h`, `config/mips/t-psp`, the `psp` thread model (`gthr-psp.h`), and `version.c`.
- **Driver (`gcc.c`):**
  - accepts the `+allegrex…` version suffix in `%v` specs
  - searches the PSP SDK (`SCE_PSP_SDK_HOME`, default `/usr/local/psp/devkit`)
  - reads its `lib/pspspecs_1_3_1` specs file
- **`c-semantics.c`:** warns when a local variable asks for more alignment than the stack provides.
- **`combine.c`:** small `make_extraction` change.
- **libstdc++:** `mipspspel` atomicity and 16-byte allocator alignment.
- **Build settings:** libgcc built without `-g`; plain `jal` in `.init`/`.fini`.
- **Japanese translation:** `gcc/po/ja.{po,gmo}`, revision 2004-07-13.

**Host fixes**, needed for a 64-bit host or a modern build environment:

- `include/obstack.h`, `cp/decl.c`: build with current GCC.
- `varasm.c`, `mips.c` (`fmask`), `cp/mangle.c` (ABI-v1 real constants):
  - remove LP64 host dependencies
  - the output is the same as the original i386-hosted compiler's
- `ltmain.sh`: deterministic archive member order.
- `gcc/Makefile.in`: fixes a parallel-make race.

## Building

```sh
PATH=/path/to/psp-binutils/bin:$PATH ./build-psp-gcc.sh install
```

`build-psp-gcc.sh` configures with the same options as the original and
installs to `PREFIX` (default `/usr/local/psp/gcc-1.3.1`). For details, see
the comments at the top of the script.

Requirements:

- the psp binutils in `PATH`
- the target C library (newlib) headers and libraries in `$PREFIX/psp/include` and `$PREFIX/psp/lib`

## Verification

Everything below was compared against the original release. The original
binaries ran under an i386 glibc.

- **`cc1`/`cc1plus` output is byte-identical:**
  - `gcc.c-torture` (1180 files, 12 option sets)
  - `gcc.dg` (904 files)
  - `g++.dg` + `g++.old-deja` (3955 files, `-O0`/`-O2`/`-Os`)
- **Internals match:**
  - instruction patterns, operands and templates
  - insn attributes, function units and conflict matrices
  - optab enable conditions (8832 configurations)
  - `rtx_cost`
  - RTL produced by the expanders
- **Driver:**
  - specs (`-dumpspecs`) and search paths are identical
  - `-###` output, including the SDK handling, differs only in temporary file names and the "Configured with" path
- **Installed files:**
  - `libgcc.a` members, `crt{begin,end,i,n}.o`, the specs file, and the C and C++ headers are byte-identical
  - the file list is identical
- **`libstdc++.a`/`libsupc++.a`:**
  - member order is identical
  - after `--strip-debug`, every member is identical except four
  - those four differ only in the random suffix of anonymous-namespace / global-constructor symbol names, which GCC generates per compile
  - the DWARF records the build directory
- **Message catalogs:** `gcc.mo` is identical for every language.

Not reproduced:

- The `*mips.md:LINE` names of unnamed patterns (shown by `-dp`). The
  original `mips.md` has more lines in places.
