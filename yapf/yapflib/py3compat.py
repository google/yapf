# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utilities for Python2 / Python3 compatibility."""

import sys

PY3 = sys.version_info[0] == 3


if PY3:
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO

    range = range
    ifilter = filter
else:
    import cStringIO
    StringIO = BytesIO = cStringIO.StringIO

    range = xrange

    from itertools import ifilter


def EncodeForStdout(s):
  """Encode the given string for emission to stdout.

  The string may contain non-ascii characters. This is a problem when stdout is
  redirected, because then Python doesn't know the encoding and we may get a
  UnicodeEncodeError.
  """
  if PY3:
    return s
  else:
    return s.encode('UTF-8')
