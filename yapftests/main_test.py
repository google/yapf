# -*- coding: utf-8 -*-
# Copyright 2015-2016 Google Inc. All Rights Reserved.
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

from contextlib import contextmanager
import sys
import unittest
import yapf

try:
  from StringIO import StringIO
except ImportError:  # Python 3
  # Note: io.StringIO is different in Python 2, so try for python 2 first.
  from io import StringIO


@contextmanager
def captured_output():
  new_out, new_err = StringIO(), StringIO()
  old_out, old_err = sys.stdout, sys.stderr
  try:
    sys.stdout, sys.stderr = new_out, new_err
    yield sys.stdout, sys.stderr
  finally:
    sys.stdout, sys.stderr = old_out, old_err


@contextmanager
def patched_input(code):
  "Monkey patch code as though it were coming from stdin."

  def lines():
    for line in code.splitlines():
      yield line
    raise EOFError()

  def patch_raw_input(lines=lines()):
    return next(lines)

  try:
    raw_input = yapf.py3compat.raw_input
    yapf.py3compat.raw_input = patch_raw_input
    yield
  finally:
    yapf.py3compat.raw_input = raw_input


class RunMainTest(unittest.TestCase):

  def testShouldHandleYapfError(self):
    """run_main should handle YapfError and sys.exit(1)"""
    expected_message = 'yapf: Input filenames did not match any python files\n'
    sys.argv = ['yapf', 'foo.c']
    with captured_output() as (out, err):
      with self.assertRaises(SystemExit):
        yapf.run_main()
      self.assertEqual(out.getvalue(), '')
      self.assertEqual(err.getvalue(), expected_message)


class MainTest(unittest.TestCase):

  def testNoPythonFilesMatched(self):
    with self.assertRaisesRegexp(yapf.errors.YapfError,
                                 'did not match any python files'):
      yapf.main(['yapf', 'foo.c'])

  def testEchoInput(self):
    code = "a = 1\nb = 2\n"
    with patched_input(code):
      with captured_output() as (out, err):
        ret = yapf.main([])
        self.assertEqual(ret, 0)
        self.assertEqual(out.getvalue(), code)

  def testEchoInputWithStyle(self):
    code = "def f(a = 1):\n    return 2*a\n"
    chromium_code = "def f(a=1):\n  return 2 * a\n"
    with patched_input(code):
      with captured_output() as (out, err):
        ret = yapf.main(['-', '--style=chromium'])
        self.assertEqual(ret, 2)
        self.assertEqual(out.getvalue(), chromium_code)

  def testEchoBadInput(self):
    bad_syntax = "  a = 1\n"
    with patched_input(bad_syntax):
      with captured_output() as (out, err):
        with self.assertRaisesRegexp(SyntaxError, "unexpected indent"):
          yapf.main([])

  def testHelp(self):
    with captured_output() as (out, err):
      ret = yapf.main(['-', '--style-help', '--style=pep8'])
      self.assertEqual(ret, 0)
      help_message = out.getvalue()
      self.assertIn("INDENT_WIDTH=4", help_message)
      self.assertIn("The number of spaces required before a trailing comment.",
                    help_message)

  def testVersion(self):
    with captured_output() as (out, err):
      ret = yapf.main(['-', '--version'])
      self.assertEqual(ret, 0)
      version = 'yapf {}\n'.format(yapf.__version__)
      self.assertEqual(version, out.getvalue())
