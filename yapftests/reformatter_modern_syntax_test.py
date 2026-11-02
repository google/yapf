# Copyright 2026 AngelaMos. All Rights Reserved.
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
"""Golden tests for Python 3.11-3.14 syntax under several styles."""

import io
import os
import unittest

from yapf.yapflib import style
from yapf.yapflib import yapf_api

from yapftests import yapf_test_helper

_TESTDATA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'testdata', 'modern_syntax')

_STYLES = ('pep8', 'google', 'facebook', 'custom')


def _StyleConfig(style_name):
  if style_name == 'custom':
    return os.path.join(_TESTDATA_DIR, 'custom.style')
  return style_name


def _ReadTestData(filename):
  with io.open(
      os.path.join(_TESTDATA_DIR, filename), encoding='utf-8',
      newline='') as fd:
    return fd.read()


class ModernSyntaxGoldenTest(yapf_test_helper.YAPFTest):

  def tearDown(self):
    style.SetGlobalStyle(style.CreatePEP8Style())

  def _CheckGolden(self, case, style_name):
    unformatted_code = _ReadTestData(case + '.in')
    expected_formatted_code = _ReadTestData(case + '.' + style_name + '.out')
    style_config = _StyleConfig(style_name)
    formatted_code, _ = yapf_api.FormatCode(
        unformatted_code, style_config=style_config)
    self.assertCodeEqual(expected_formatted_code, formatted_code)
    reformatted_code, _ = yapf_api.FormatCode(
        formatted_code, style_config=style_config)
    self.assertCodeEqual(formatted_code, reformatted_code)


def _MakeGoldenTest(case, style_name):

  def Test(self):
    self._CheckGolden(case, style_name)

  return Test


def _AddGoldenTests():
  for filename in sorted(os.listdir(_TESTDATA_DIR)):
    if not filename.endswith('.in'):
      continue
    case = filename[:-len('.in')]
    for style_name in _STYLES:
      setattr(ModernSyntaxGoldenTest, 'testGolden_%s_%s' % (case, style_name),
              _MakeGoldenTest(case, style_name))


_AddGoldenTests()

if __name__ == '__main__':
  unittest.main()
