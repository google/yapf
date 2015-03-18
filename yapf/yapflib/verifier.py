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
"""Verify that the generated code is valid code.

This takes a line of code and "normalizes" it. I.e., it transforms the snippet
into something that has the potential to compile.

    VerifyCode(): the main function exported by this module.
"""

import ast
import re
import sys
import textwrap


def VerifyCode(code):
  """Verify that the reformatted code is syntactically correct.

  Arguments:
    code: (unicode) The reformatted code snippet.

  Raises:
    SyntaxError if the code was reformatted incorrectly.
  """
  try:
    compile(textwrap.dedent(code).encode('UTF-8'), '<string>', 'exec')
  except SyntaxError:
    try:
      ast.parse(textwrap.dedent(code.lstrip('\n')).lstrip(), '<string>', 'exec')
    except SyntaxError:
      try:
        normalized_code = _NormalizeCode(code)
        compile(normalized_code.encode('UTF-8'), '<string>', 'exec')
      except SyntaxError:
        sys.stderr.write('INTERNAL ERROR: %s\n' % code)
        raise


def _NormalizeCode(code):
  """Make sure that the code snippet is compilable."""
  code = textwrap.dedent(code.lstrip('\n')).lstrip()

  if re.match(r'(if|while|for|with|def|class)\b', code):
    code += '\n    pass'
  elif re.match(r'(elif|else)\b', code):
    code = 'if True:\n    pass\n' + code + '\n    pass'
  elif code.startswith('@'):
    code += '\ndef _():\n    pass'
  elif re.match(r'try\b', code):
    code += '\n    pass\nexcept:\n    pass'
  elif re.match(r'(except|finally)\b', code):
    code = 'try:\n    pass\n' + code + '\n    pass'
  elif re.match(r'(return|yield)\b', code):
    code = 'def _():\n    ' + code
  elif re.match(r'(continue|break)\b', code):
    code = 'while True:\n    ' + code
  elif re.match(r'print\b', code):
    code = 'from __future__ import print_function\n' + code

  return code + '\n'
