/* Definitions of target machine for GNU compiler.
   Sony PlayStation Portable (Allegrex) version.
   Copyright (C) 2004 Free Software Foundation, Inc.

This file is part of GNU CC.

GNU CC is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2, or (at your option)
any later version.

GNU CC is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with GNU CC; see the file COPYING.  If not, write to
the Free Software Foundation, 59 Temple Place - Suite 330,
Boston, MA 02111-1307, USA.  */

/* The Allegrex is a single precision, hard float, little endian MIPS II
   derivative; refuse options that ask for anything else.  */

#undef SUBTARGET_CC1_SPEC
#define SUBTARGET_CC1_SPEC "\
%{mhard-float:%e-mhard-float not supported} \
%{msoft-float:%e-msoft-float not supported} \
%{!G:-G 0} \
%{mcpu=*:%e-mcpu not supported} \
%{march=*:%e-march not supported} \
%{mtune=*:%e-mtune not supported} \
%{mips3:%e-mips3 not supported} \
%{mips4:%e-mips4 not supported} \
-march=allegrex -mtune=allegrex \
%{!mulsw:-mno-ulsw}"

#undef SUBTARGET_CPP_SPEC
#define SUBTARGET_CPP_SPEC "\
%{msoft-float:%e-msoft-float not supported} \
%{mhard-float:%e-mhard-float not supported} \
-D__mips_hard_float -D__mips_single_float"

#undef CPP_PREDEFINES
#define CPP_PREDEFINES "\
-DMIPSEL -DR3000 -D_MIPSEL -D_R3000 \
-D__SCE__ -D__psp__ -D__psp_gcc__=0x010701"

#undef LIB_SPEC
#define LIB_SPEC "-lc"

#undef MULTILIB_DEFAULTS
#define MULTILIB_DEFAULTS { "EL" }

/* Do not put data in the small data section by default.  */
#undef MIPS_DEFAULT_GVALUE
#define MIPS_DEFAULT_GVALUE 0

/* Allow objects (e.g. VFPU vectors) to be aligned to 16 bytes.  */
#undef BIGGEST_ALIGNMENT
#define BIGGEST_ALIGNMENT 128

/* Identify the compiler in the assembler output.  */
#undef IDENT_ASM_OP
#define IDENT_ASM_OP "\t.ident\t"

/* Output common and local symbols with their alignment, ELF style.  */
#undef ASM_OUTPUT_ALIGNED_DECL_COMMON
#undef ASM_OUTPUT_LOCAL

#undef COMMON_ASM_OP
#define COMMON_ASM_OP	"\t.comm\t"

#undef  ASM_OUTPUT_ALIGNED_COMMON
#define ASM_OUTPUT_ALIGNED_COMMON(FILE, NAME, SIZE, ALIGN)		\
  do									\
    {									\
      fprintf ((FILE), "%s", COMMON_ASM_OP);				\
      assemble_name ((FILE), (NAME));					\
      fprintf ((FILE), ",%u,%u\n", (SIZE), (ALIGN) / BITS_PER_UNIT);	\
    }									\
  while (0)

#undef LOCAL_ASM_OP
#define LOCAL_ASM_OP	"\t.local\t"

#undef  ASM_OUTPUT_ALIGNED_LOCAL
#define ASM_OUTPUT_ALIGNED_LOCAL(FILE, NAME, SIZE, ALIGN)	\
  do								\
    {								\
      fprintf ((FILE), "%s", LOCAL_ASM_OP);			\
      assemble_name ((FILE), (NAME));				\
      fprintf ((FILE), "\n");					\
      ASM_OUTPUT_ALIGNED_COMMON (FILE, NAME, SIZE, ALIGN);	\
    }								\
  while (0)

/* The startup code does not use $gp, so .init and .fini just call
   the static functions.  */
#undef CRT_CALL_STATIC_FUNCTION
#define CRT_CALL_STATIC_FUNCTION(SECTION_OP, FUNC)	\
   asm (SECTION_OP "\n\
	jal " USER_LABEL_PREFIX #FUNC "\n\
	" TEXT_SECTION_ASM_OP);

/* Location of the PSP SDK ("devkit").  The driver searches its include,
   bin and lib directories and reads the SDK specs file from its lib
   directory; the environment variable overrides the default location.  */
#define PSP_SDK_HOME_ENV	"SCE_PSP_SDK_HOME"
#define PSP_SDK_HOME_DEFAULT	"/usr/local/psp/devkit"
#define PSP_SDK_SPECS_FILE	"/lib/pspspecs_1_7_1"
