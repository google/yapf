# Copyright 2020 Google Inc. All Rights Reserved.
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
"""Fixer that enforces consistent use of quotes for strings.

All strings should use the same quotes. The exception being when the opposite
quote is used in the string itself --- i.e., '"' or "'". This also changes a
docstring that uses ''' into one that uses double quotes, which is the required
format.
"""

import re

from contrib.fixers import line_conditional_fix


class FixQuotes(line_conditional_fix.LineConditionalFix):
  """Fixer for consistent use of quotes in strings."""

  explicit = True  # The user must ask for this fixer.

  # Assorted regex patterns.
  _delim_pattern = re.compile(r'^[uUbB]?[rR]?(?P<delim>"""|\'\'\'|"|\')')
  _dbl_quote_pattern = re.compile(r'(^[uUbB]?[rR]?)"([^"]*)"$')
  _sgl_quote_pattern = re.compile(r"(^[uUbB]?[rR]?)'([^']*)'$")
  _multiline_string_quote_pattern = re.compile(
      r"(?s)(^[uUbB]?[rR]?)'''(.*?)'''$")

  PATTERN = """STRING"""

  def __init__(self, options, log):
    super(FixQuotes, self).__init__(options, log)

    # The option force_quote_type permits forcing the quote style this fixer
    # will enforce, regardless of what currently exists in the file.
    # When it's 'none' or doesn't exist, there's no forcing and a heuristic
    # is used to determine which quote style to use.
    forced_quote_type = options.get('force_quote_type', 'none')
    if forced_quote_type == 'single':
      self._string_delim = "'"
    elif forced_quote_type == 'double':
      self._string_delim = '"'
    else:
      assert forced_quote_type == 'none'
      self._string_delim = None

  def transform(self, node, results):
    if self.should_skip(node) or not node.parent:
      return

    first_delim = self._GetDelimiter(node.value)
    if first_delim == "'''" and '"""' not in node.value[3:-3]:
      # Always use """ for docstrings and multiline strings.
      if node.value[-4] != '"':
        new = node.clone()
        new.parent = node.parent
        new.value = re.sub(self._multiline_string_quote_pattern, r'\1"""\2"""',
                           node.value)
        return new
      return

    if ((first_delim == '"' and "'" in node.value[1:-1]) or
        (first_delim == "'" and '"' in node.value[1:-1])):
      return

    if self._string_delim is None:
      self._string_delim = first_delim

    elif first_delim != self._string_delim:
      # The quote isn't consistent.
      new = node.clone()
      new.parent = node.parent
      if self._string_delim == '"':
        new.value = re.sub(self._sgl_quote_pattern, r'\1"\2"', node.value)
      else:
        new.value = re.sub(self._dbl_quote_pattern, r"\1'\2'", node.value)
      return new

  def _GetDelimiter(self, string):
    """Return the delimiter for the given string repr, omitting prefix."""
    match = re.search(self._delim_pattern, string)
    if not match:
      return None
    return match.group('delim')
