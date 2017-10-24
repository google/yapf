# Copyright 2016-2017 Google Inc. All Rights Reserved.
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
"""Basic tests for yapf.reformatter."""

import textwrap
import unittest

from yapf.yapflib import reformatter
from yapf.yapflib import style

from yapftests import yapf_test_helper


class BasicReformatterTest(yapf_test_helper.YAPFTest):

  @classmethod
  def setUpClass(cls):
    style.SetGlobalStyle(style.CreatePEP8Style())

  def test_fail(self):
    formatted_code = textwrap.dedent("""\
        expected_status = {
            'status': False,
            'statusMessages': [{
                'code': 'CORE_0001',
                'parameters': {},
                'target': 'amount',
            }]
        }
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(formatted_code)
    self.assertCodeEqual(formatted_code, reformatter.Reformat(uwlines))

  def test_pass(self):
    formatted_code = textwrap.dedent("""\
        expected_status = {
            'status': False,
            'statusMessages': [{
                1: 2,
                'parameters': {},
                'target': 'amount',
            }]
        }
        """)
    uwlines = yapf_test_helper.ParseAndUnwrap(formatted_code)
    self.assertCodeEqual(formatted_code, reformatter.Reformat(uwlines))

if __name__ == '__main__':
  unittest.main()
