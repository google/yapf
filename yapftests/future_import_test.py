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
"""Test for __future__ import code verification."""

import __future__
import textwrap
import unittest

from yapf.yapflib import yapf_api
from yapf.yapflib import reformatter

class FuturePrintTest(unittest.TestCase):

  def testExtractSingleFutureImport(self):
    """Extract a single import from __future__"""
    code = textwrap.dedent("""\
      from __future__ import print_function
      """)
    flags = reformatter._ExtractFutureImports(code)
    self.assertEqual(flags, __future__.print_function.compiler_flag)

  def testExtractMultipleFutureImportsLines(self):
    """Extract multiple __future__ imports on separate lines"""
    code = textwrap.dedent("""\
      from __future__ import print_function
      from __future__ import absolute_import
      """)
    flags = reformatter._ExtractFutureImports(code)
    expected_flags = __future__.print_function.compiler_flag | \
                     __future__.absolute_import.compiler_flag
    self.assertEqual(flags, expected_flags)

  def testExtractMultipleFutureImportsParentheses(self):
    """Extract multiple __future__ imports within parentheses"""
    code = textwrap.dedent("""\
      from __future__ import (print_function, absolute_import)
      """)
    flags = reformatter._ExtractFutureImports(code)
    expected_flags = __future__.print_function.compiler_flag | \
                     __future__.absolute_import.compiler_flag
    self.assertEqual(flags, expected_flags)

  def testExtractMultipleFutureImportsParenthesesLines(self):
    """Extract multiple __future__ imports within parentheses on two lines"""
    code = textwrap.dedent("""\
      from __future__ import (print_function,
        absolute_import)
      """)
    flags = reformatter._ExtractFutureImports(code)
    expected_flags = __future__.print_function.compiler_flag | \
                     __future__.absolute_import.compiler_flag
    self.assertEqual(flags, expected_flags)

  def testExtractMultipleFutureImportsLinesEscape(self):
    """Extract multiple __future__ imports with newline escaped"""
    code = textwrap.dedent("""\
      from __future__ import print_function, \
        absolute_import
      """)
    flags = reformatter._ExtractFutureImports(code)
    expected_flags = __future__.print_function.compiler_flag | \
                     __future__.absolute_import.compiler_flag
    self.assertEqual(flags, expected_flags)

  def testExtractCorrectFutureImportsWhenImportedAsAnother(self):
    """Extract only the correct imports when one is imported as another"""
    code = textwrap.dedent("""\
      from __future__ import print_function as absolute_import
      """)
    flags = reformatter._ExtractFutureImports(code)
    self.assertEqual(flags, __future__.print_function.compiler_flag)

  def testFuturePrintPassToFunction(self):
    """
    Pass print() to a function as print("x") is still valid w/o future import
    """
    code = textwrap.dedent("""\
      from __future__ import print_function
      def use_function(fnc):
        fnc("test")
      if __name__ == "__main__":
        use_function(print)
      """)

    try:
      yapf_api.FormatCode(code)
    except SyntaxError:
      self.fail("FormatCode() did not handle future import correctly.")
