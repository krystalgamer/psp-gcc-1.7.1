/* A host-independent qsort.
   Based on the merge sort of the GNU C Library (stdlib/msort.c),
   written by Mike Haertel.
   Copyright (C) 1992, 1995-1997, 1999, 2000, 2001, 2002
   Free Software Foundation, Inc.

This file is part of the libiberty library.
Libiberty is free software; you can redistribute it and/or
modify it under the terms of the GNU Library General Public
License as published by the Free Software Foundation; either
version 2 of the License, or (at your option) any later version.

Libiberty is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Library General Public License for more details.

You should have received a copy of the GNU Library General Public
License along with libiberty; see the file COPYING.LIB.  If
not, write to the Free Software Foundation, Inc., 59 Temple Place - Suite 330,
Boston, MA 02111-1307, USA.  */

/*

@deftypefn Extension void stable_qsort (void *@var{base}, size_t @var{nmemb}, size_t @var{size}, int (*@var{compar})(const void *, const void *))

Sort an array like @code{qsort}, using the merge sort of the GNU C
library's @code{qsort}: the same elements are compared in the same
order, so the result is the same as with that library even when
@var{compar} considers different elements equal.  The sort is stable.

@end deftypefn

*/

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif
#include "ansidecl.h"
#include "libiberty.h"

#include <stddef.h>
#ifdef HAVE_STDLIB_H
#include <stdlib.h>
#endif
#ifdef HAVE_STRING_H
#include <string.h>
#endif

static void msort_with_tmp PARAMS ((char *, size_t, size_t,
				    int (*) (const void *, const void *),
				    char *));

static void
msort_with_tmp (b, n, s, cmp, t)
     char *b;
     size_t n;
     size_t s;
     int (*cmp) PARAMS ((const void *, const void *));
     char *t;
{
  char *tmp;
  char *b1, *b2;
  size_t n1, n2;

  if (n <= 1)
    return;

  n1 = n / 2;
  n2 = n - n1;
  b1 = b;
  b2 = b + n1 * s;

  msort_with_tmp (b1, n1, s, cmp, t);
  msort_with_tmp (b2, n2, s, cmp, t);

  tmp = t;
  while (n1 > 0 && n2 > 0)
    {
      if ((*cmp) (b1, b2) <= 0)
	{
	  memcpy (tmp, b1, s);
	  b1 += s;
	  --n1;
	}
      else
	{
	  memcpy (tmp, b2, s);
	  b2 += s;
	  --n2;
	}
      tmp += s;
    }
  if (n1 > 0)
    memcpy (tmp, b1, n1 * s);
  memcpy (b, t, (n - n2) * s);
}

void
stable_qsort (base, nmemb, size, compar)
     void *base;
     size_t nmemb;
     size_t size;
     int (*compar) PARAMS ((const void *, const void *));
{
  char *tmp;

  if (nmemb <= 1)
    return;

  tmp = (char *) xmalloc (nmemb * size);
  msort_with_tmp ((char *) base, nmemb, size, compar, tmp);
  free (tmp);
}
