# -*- coding: utf-8 -*-
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
"""Tests for yapf.__init__.main."""

import sys
import unittest
from contextlib import contextmanager
from io import StringIO

import yapf

from yapftests import yapf_test_helper


class IO(object):
  """IO is a thin wrapper around StringIO.

  This is strictly to wrap the Python 3 StringIO object so that it can supply a
  "buffer" attribute.
  """

  class Buffer(object):

    def __init__(self):
      self.string_io = StringIO()

    def write(self, s):
      if isinstance(s, bytes):
        s = str(s, 'utf-8')
      self.string_io.write(s)

    def getvalue(self):
      return self.string_io.getvalue()

  def __init__(self):
    self.buffer = self.Buffer()

  def write(self, s):
    self.buffer.write(s)

  def getvalue(self):
    return self.buffer.getvalue()


@contextmanager
def captured_output():
  new_out, new_err = IO(), IO()
  old_out, old_err = sys.stdout, sys.stderr
  try:
    sys.stdout, sys.stderr = new_out, new_err
    yield sys.stdout, sys.stderr
  finally:
    sys.stdout, sys.stderr = old_out, old_err


@contextmanager
def patched_input(code):
  """Monkey patch code as though it were coming from stdin."""

  def lines():
    for line in code.splitlines():
      yield line
    raise EOFError()

  def patch_raw_input(lines=lines()):
    return next(lines)

  try:
    orig_raw_import = yapf._raw_input
    yapf._raw_input = patch_raw_input
    yield
  finally:
    yapf._raw_input = orig_raw_import


class RunMainTest(yapf_test_helper.YAPFTest):

  def testShouldHandleYapfError(self):
    """run_main should handle YapfError and sys.exit(1)."""
    expected_message = 'yapf: input filenames did not match any python files\n'
    sys.argv = ['yapf', 'foo.c']
    with captured_output() as (out, err):
      with self.assertRaises(SystemExit):
        yapf.run_main()
      self.assertEqual(out.getvalue(), '')
      self.assertEqual(err.getvalue(), expected_message)


class MainTest(yapf_test_helper.YAPFTest):

  def testNoPythonFilesMatched(self):
    with self.assertRaisesRegex(yapf.errors.YapfError,
                                'did not match any python files'):
      yapf.main(['yapf', 'foo.c'])

  def testEchoInput(self):
    code = 'a = 1\nb = 2\n'
    with patched_input(code):
      with captured_output() as (out, _):
        ret = yapf.main([])
        self.assertEqual(ret, 0)
        self.assertEqual(out.getvalue(), code)

  def testEchoInputWithStyle(self):
    code = 'def f(a = 1\n\n):\n    return 2*a\n'
    yapf_code = 'def f(a=1):\n  return 2 * a\n'
    with patched_input(code):
      with captured_output() as (out, _):
        ret = yapf.main(['-', '--style=yapf'])
        self.assertEqual(ret, 0)
        self.assertEqual(out.getvalue(), yapf_code)

  def testEchoBadInput(self):
    bad_syntax = '  a = 1\n'
    with patched_input(bad_syntax):
      with captured_output() as (_, _):
        with self.assertRaisesRegex(yapf.errors.YapfError, 'unexpected indent'):
          yapf.main([])

  def testHelp(self):
    with captured_output() as (out, _):
      ret = yapf.main(['-', '--style-help', '--style=pep8'])
      self.assertEqual(ret, 0)
      help_message = out.getvalue()
      self.assertIn('indent_width=4', help_message)
      self.assertIn('The number of spaces required before a trailing comment.',
                    help_message)
