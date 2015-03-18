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

import sys
import unittest

from yapftests import blank_line_calculator_test
from yapftests import blank_line_calculator_test
from yapftests import comment_splicer_test
from yapftests import format_decision_state_test
from yapftests import format_token_test
from yapftests import line_joiner_test
from yapftests import pytree_unwrapper_test
from yapftests import pytree_utils_test
from yapftests import pytree_visitor_test
from yapftests import reformatter_test
from yapftests import split_penalty_test
from yapftests import subtype_assigner_test
from yapftests import unwrapped_line_test
from yapftests import yapf_test


def suite():
  result = unittest.TestSuite()
  result.addTests(blank_line_calculator_test.suite())
  result.addTests(blank_line_calculator_test.suite())
  result.addTests(comment_splicer_test.suite())
  result.addTests(format_decision_state_test.suite())
  result.addTests(format_token_test.suite())
  result.addTests(line_joiner_test.suite())
  result.addTests(pytree_unwrapper_test.suite())
  result.addTests(pytree_utils_test.suite())
  result.addTests(pytree_visitor_test.suite())
  result.addTests(reformatter_test.suite())
  result.addTests(split_penalty_test.suite())
  result.addTests(subtype_assigner_test.suite())
  result.addTests(unwrapped_line_test.suite())
  result.addTests(yapf_test.suite())
  return result


if __name__ == '__main__':
  runner = unittest.TextTestRunner()
  result = runner.run(suite())
  sys.exit(not result.wasSuccessful())
