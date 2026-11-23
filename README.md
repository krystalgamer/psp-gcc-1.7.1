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
- emulation of the original `cc1`
- decompiled functions
- the installed headers, specs, libraries and message catalogs

The reconstruction was then checked by rebuilding with the original
toolchain (see "Verification"). Binutils are not covered here.

## Branches

- **`sony`**: FSF GCC 3.3.3 plus the reconstructed PSP changes, and nothing
  else. Built on Red Hat Linux 9 with its gcc 3.2.2, as the original was, it
  reproduces the original executables.
- **`master`**: `sony` plus the changes needed to build and run correctly on
  modern and 64-bit hosts, the build script and this README. It produces the
  same compiler output as the original.

Patch series:

```sh
git format-patch fsf-gcc-3.3.3..sony -- gcc-3.3.3    # the PSP changes
git format-patch sony..master -- gcc-3.3.3           # the host/x64 port
```

## Changes

**PSP changes (`sony`):**

- **Allegrex processor support (`config/mips/mips.{h,c,md}`, `mips-protos.h`):**
  - `-march=allegrex{,2,3,31}`
  - `-m[no-]ulsw`, `-m[no-]ext`, `-m[no-]madd`
  - Allegrex instructions: `clz`/`clo`, `seb`/`seh`, `bitrev`, `wsbh`/`wsbw`, `ext`/`ins`, `min`/`max`, `movz`/`movn`, `rotr`, `madd`/`msub`, and the FP rounding conversions
  - `__builtin_allegrex_*` builtins
  - function units and costs
  - block move strategy
  - 16-byte stack alignment for Allegrex 3.1
- **Target configuration:**
  - `config.gcc`, `config.sub`, `config/mips/psp.h`, `config/mips/t-psp`
  - the `psp` thread model (`gthr-psp.h`)
  - `version.c`
  - libgcc built without `-g`, plain `jal` in `.init`/`.fini`
  - default `-G 0`
- **Driver (`gcc.c`):**
  - accepts the `+allegrex…` version suffix in `%v` specs
  - searches the PSP SDK (`SCE_PSP_SDK_HOME`, default `/usr/local/psp/devkit`)
  - reads its `lib/pspspecs_1_3_1` specs file
- **`cpplex.c`:** with `--enable-c-mbchar`, string literals with Shift-JIS characters whose second byte is `\` are handled correctly. Stock 3.3.3 also stored wrong bytes for any multibyte character.
- **`combine.c`:**
  - in comparisons, an AND with any contiguous run of ones becomes a bit-field extract
  - wide low-order extracts are kept
- **`c-semantics.c`:** warns when a local variable asks for more alignment than the stack provides.
- **libstdc++:** `mipspspel` atomicity and 16-byte allocator alignment.
- **Japanese translation:** `gcc/po/ja.{po,gmo}`, revision 2004-07-13.

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

### `sony` on the original toolchain

`tools/rh9-i386-build.sh` builds the `sony` branch the way the original was built. It needs `bwrap`; no root and no Red Hat installation required.

- **Environment:**
  - Red Hat Linux 9 gcc 3.2.2-5 and binutils 2.13.90.0.18-9
  - glibc 2.3.2-27.9.7 (i686), the version the original was linked against
  - default `-g -O2`, configured from a sibling directory
  - binaries stripped with `strip -g`, like rpmbuild's `brp-strip`
- **Results:**
  - **byte-identical to the original:** `psp-gcc`, `psp-cpp` and `collect2`
  - **`cc1`/`cc1plus`:** 5549 of 5560 functions are identical (6811 of 6822 in `cc1plus`), including the line numbers in every `abort()` call
  - the remaining 11 differ in code shape only:
    - 9 come from genattrtab's function-unit tables: `*_unit_*`, `function_units_used`, `result_ready_cost`, `insn_latency`, `min_insn_conflict_delay`. They depend on the exact order of the `define_function_unit` rules; their values are identical.
    - in `block_move_loop_allegrex`, two variables swap a register and a stack slot
    - in `output_334`, the peephole pass picks different scratch registers
  - `tools/fcmp.py` compares two executables function by function

### `master` on a modern x86_64 host

Everything below was compared against the original release. The original
binaries ran under an i386 glibc.

- **`cc1`/`cc1plus` output is byte-identical**, including `-dp` output:
  - `gcc.c-torture` (1180 files, 12 option sets)
  - `gcc.dg` (904 files)
  - `g++.dg` + `g++.old-deja` (3955 files, `-O0`/`-O2`/`-Os`)
  - Shift-JIS/EUC-JP string tests
- **Internals match:**
  - instruction patterns, operands and templates
  - insn attributes, function units and conflict matrices
  - optab enable conditions (8832 configurations)
  - `rtx_cost`
  - RTL produced by the expanders
- **Driver:** specs and search paths are identical; `-###` output, including the SDK handling, differs only in temporary file names and the "Configured with" path.
- **Installed files:**
  - `libgcc.a` members, `crt{begin,end,i,n}.o`, the specs file, and the C and C++ headers are byte-identical
  - the file list is identical
- **`libstdc++.a`/`libsupc++.a`:**
  - member order is identical
  - after `--strip-debug`, every member is identical except four
  - in those four, the only differing bytes are the six-character random suffixes of anonymous-namespace / global-constructor symbol names, which GCC derives from the time and process ID of each compile
- **Message catalogs:** `gcc.mo` is identical for every language.
