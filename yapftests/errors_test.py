# Copyright 2026 Google Inc. All Rights Reserved.
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
"""Tests for yapf.errors."""

import configparser

from yapf_third_party._ylib2to3.pgen2 import parse
from yapf_third_party._ylib2to3.pgen2 import tokenize

from yapf.yapflib import errors
from yapftests import yapf_test_helper


class ErrorsTest(yapf_test_helper.YAPFTest):

  def testFormatSyntaxError(self):
    e = SyntaxError('invalid syntax', ('foo.py', 10, 5, 'x ='))
    msg = errors.FormatErrorMsg(e)
    self.assertEqual(msg, 'foo.py:10:5: invalid syntax')

  def testFormatTokenError(self):
    e = tokenize.TokenError('EOF in multi-line string', (3, 7))
    e.filename = 'bar.py'
    msg = errors.FormatErrorMsg(e)
    self.assertEqual(msg, 'bar.py:3:7: EOF in multi-line string')

  def testFormatParseError(self):
    e = parse.ParseError('bad input', 1, 'ROI', ('', (9, 39)))
    e.filename = 'baz.py'
    msg = errors.FormatErrorMsg(e)
    self.assertEqual(msg, "baz.py:9:39: bad input: 'ROI'")

  def testFormatParseErrorNoContext(self):
    e = parse.ParseError('unexpected EOF', 0, '', None)
    msg = errors.FormatErrorMsg(e)
    self.assertEqual(msg, '<unknown>:1:0: unexpected EOF')

  def testFormatMissingSectionHeaderError(self):
    e = configparser.MissingSectionHeaderError('style.yapf', 1, 'foo = bar')
    msg = errors.FormatErrorMsg(e)
    self.assertIn('File contains no section headers.', msg)
    self.assertIn('style.yapf', msg)

  def testFormatGenericExceptionWithFilename(self):
    e = ValueError('invalid setting')
    e.filename = 'qux.py'
    msg = errors.FormatErrorMsg(e)
    self.assertEqual(msg, 'qux.py: invalid setting')

  def testFormatGenericExceptionWithoutFilename(self):
    e = RuntimeError('unexpected failure')
    msg = errors.FormatErrorMsg(e)
    self.assertEqual(msg, 'unexpected failure')
