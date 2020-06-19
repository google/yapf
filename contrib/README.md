# YAPF contrib

Any code in this directory is not officially supported, and may change or be
removed at any time without notice.

The `contrib/` directory contains external contributions to YAPF, which aren't
part of its official code base. In particular, `lib2to3` "fixers" are added
here. They aren't part of YAPF, because they modify non-whitespace in source
code, which is against the YAPF philosophy.

The code in this directory may not be tested on a regular basis, and thus
should be used with caution.
