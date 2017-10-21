# Copyright 2015-2017 Google Inc. All Rights Reserved.
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

import io
import os
import re
import sys

PY3 = sys.version_info[0] >= 3
PY36 = sys.version_info[0] >= 3 and sys.version_info[1] >= 6

if PY3:
  StringIO = io.StringIO
  BytesIO = io.BytesIO

  import codecs

  def open_with_encoding(filename, mode, encoding, newline=''):  # pylint: disable=unused-argument
    return codecs.open(filename, mode=mode, encoding=encoding)

  import functools
  lru_cache = functools.lru_cache

  range = range
  ifilter = filter
  raw_input = input

  def readline():
    return sys.stdin.buffer.readline()

  import configparser

  # Mappings from strings to booleans (such as '1' to True, 'false' to False,
  # etc.)
  CONFIGPARSER_BOOLEAN_STATES = configparser.ConfigParser.BOOLEAN_STATES
else:
  import __builtin__
  import cStringIO
  StringIO = BytesIO = cStringIO.StringIO

  open_with_encoding = io.open

  # Python 2.7 doesn't have a native LRU cache, so do nothing.
  def lru_cache(maxsize=128, typed=False):

    def fake_wrapper(user_function):
      return user_function

    return fake_wrapper

  range = xrange

  from itertools import ifilter
  raw_input = raw_input

  def readline():
    return sys.stdin.readline()

  import ConfigParser as configparser
  CONFIGPARSER_BOOLEAN_STATES = configparser.ConfigParser._boolean_states  # pylint: disable=protected-access


def EncodeAndWriteToStdout(s, encoding='utf-8'):
  """Encode the given string and emit to stdout.

  The string may contain non-ascii characters. This is a problem when stdout is
  redirected, because then Python doesn't know the encoding and we may get a
  UnicodeEncodeError.

  Arguments:
    s: (string) The string to encode.
    encoding: (string) The encoding of the string.
  """
  if PY3:
    sys.stdout.buffer.write(s.encode(encoding))
  elif sys.platform == 'win32':
    # On python 2 and Windows universal newline transformation will be in
    # effect on stdout. Python 2 will not let us avoid the easily because
    # it happens based on whether the file handle is opened in O_BINARY or
    # O_TEXT state. However we can tell Windows itself to change the current
    # mode, and python 2 will follow suit. However we must take care to change
    # the mode on the actual external stdout not just the current sys.stdout
    # which may have been monkey-patched inside the python environment.
    import msvcrt  # pylint: disable=g-import-not-at-top
    if sys.__stdout__ is sys.stdout:
      msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    sys.stdout.write(s.encode(encoding))
  else:
    sys.stdout.write(s.encode(encoding))


if PY3:
  unicode = str  # pylint: disable=redefined-builtin,invalid-name
else:

  def unicode(s):  # pylint: disable=invalid-name
    """Force conversion of s to unicode."""
    # Avoid TypeError: decoding Unicode is not supported
    if isinstance(s, __builtin__.unicode):
      return s
    return __builtin__.unicode(s, 'utf-8')


def ProcessEncoding(original_source, is_tty):
  """Decode the source code if necessary.

  If the source code reading from stdin is from a file, try to use the
  encoding specifying in magic encoding comment. Otherwise use utf-8 as
  the default encoding.

  This decode process only takes effect when source code is from a file
  feeding to stdin. The file is not necessarily using the same encoding as
  default locale setting, it would be better to get encoding from comment.

  Arguments:
    original_source: (list of unicode or bytes) The source code reading from
      stdin.
    is_tty: (bool) The encoding of the string.

  Returns:
    A string representing the source code.
  """
  # Use utf-8 as the defualt and fallback setting
  encoding = 'utf-8'
  if not is_tty:
    # This pattern is extracted from PEP 263
    pattern = b'^[ \t\v]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+)'
    # Encoding comment only appears in the first or second line
    for line in original_source[:2]:
      match_object = re.match(pattern, line)
      if match_object:
        encoding = match_object.group(1).decode('utf-8')
        break
    source = [
        line.decode(encoding, 'backslashreplace').rstrip()
        for line in original_source
    ]
  else:
    source = [line.rstrip() for line in original_source]
  return encoding, source


# In Python 3.2+, readfp is deprecated in favor of read_file, which doesn't
# exist in Python 2 yet. To avoid deprecation warnings, subclass ConfigParser to
# fix this - now read_file works across all Python versions we care about.
class ConfigParser(configparser.ConfigParser):
  if not PY3:

    def read_file(self, fp, source=None):
      self.readfp(fp, filename=source)
