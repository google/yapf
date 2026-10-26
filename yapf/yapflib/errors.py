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
"""YAPF error objects."""

from yapf_third_party._ylib2to3.pgen2 import parse
from yapf_third_party._ylib2to3.pgen2 import tokenize


def FormatErrorMsg(e):
  """Convert an exception into a standard format.

  The standard error message format is:

      <filename>:<lineno>:<column>: <msg>

  Arguments:
    e: An exception.

  Returns:
    A properly formatted error message string.
  """
  if isinstance(e, SyntaxError):
    return '{}:{}:{}: {}'.format(
        getattr(e, 'filename', '<unknown>'),
        getattr(e, 'lineno', 1),
        getattr(e, 'offset', 0),
        getattr(e, 'msg', str(e)),
    )
  if isinstance(e, tokenize.TokenError):
    filename = getattr(e, 'filename', '<unknown>')
    lineno = (
        e.args[1][0]
        if (len(e.args) > 1 and isinstance(e.args[1], (tuple, list)) and
            len(e.args[1]) > 0)
        else 1
    )
    col = (
        e.args[1][1]
        if (len(e.args) > 1 and isinstance(e.args[1], (tuple, list)) and
            len(e.args[1]) > 1)
        else 0
    )
    msg = e.args[0] if e.args else str(e)
    return '{}:{}:{}: {}'.format(filename, lineno, col, msg)
  if isinstance(e, parse.ParseError):
    filename = getattr(e, 'filename', '<unknown>')
    lineno = 1
    col = 0
    context = getattr(e, 'context', None)
    if (context and len(context) > 1 and
        isinstance(context[1], (tuple, list)) and len(context[1]) >= 2):
      lineno, col = context[1][0], context[1][1]
    msg = getattr(e, 'msg', None)
    if msg and getattr(e, 'value', None):
      msg = '{}: {!r}'.format(msg, e.value)
    elif not msg:
      msg = str(e)
    return '{}:{}:{}: {}'.format(filename, lineno, col, msg)
  if (len(getattr(e, 'args', ())) > 1 and
      isinstance(e.args[1], (tuple, list)) and
      len(e.args[1]) >= 3):
    msg = getattr(e, 'msg', e.args[0] if e.args else str(e))
    return '{}:{}:{}: {}'.format(e.args[1][0], e.args[1][1], e.args[1][2], msg)
  filename = getattr(e, 'filename', None)
  lineno = getattr(e, 'lineno', None)
  msg = str(e)
  if filename and lineno is not None:
    return '{}:{}: {}'.format(filename, lineno, msg)
  if filename:
    return '{}: {}'.format(filename, msg)
  return msg


class YapfError(Exception):
  """Parent class for user errors or input errors.

  Exceptions of this type are handled by the command line tool
  and result in clear error messages, as opposed to backtraces.
  """
  pass
