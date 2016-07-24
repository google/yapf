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
"""Pytree nodes with extra formatting information.

This is a thin wrapper around a pytree.Leaf node.
"""

import keyword
import re

from lib2to3 import pytree
from lib2to3.pgen2 import token

from yapf.yapflib import py3compat
from yapf.yapflib import pytree_utils
from yapf.yapflib import style

CONTINUATION = token.N_TOKENS
token.N_TOKENS += 1


class Subtype(object):
  """Subtype information about tokens.

  Gleaned from parsing the code. Helps determine the best formatting.
  """
  NONE = 0
  UNARY_OPERATOR = 1
  BINARY_OPERATOR = 2
  SUBSCRIPT_COLON = 3
  SUBSCRIPT_BRACKET = 4
  DEFAULT_OR_NAMED_ASSIGN = 5
  VARARGS_STAR = 6
  KWARGS_STAR_STAR = 7
  ASSIGN_OPERATOR = 8
  DICTIONARY_KEY = 9
  DICTIONARY_VALUE = 10
  DICT_SET_GENERATOR = 11
  COMP_FOR = 12
  COMP_IF = 13
  DEFAULT_OR_NAMED_ASSIGN_ARG_LIST = 14
  FUNC_DEF = 15


class FormatToken(object):
  """A wrapper around pytree Leaf nodes.

  This represents the token plus additional information useful for reformatting
  the code.

  Attributes:
    next_token: The token in the unwrapped line after this token or None if this
      is the last token in the unwrapped line.
    previous_token: The token in the unwrapped line before this token or None if
      this is the first token in the unwrapped line.
    matching_bracket: If a bracket token ('[', '{', or '(') the matching
      bracket.
    whitespace_prefix: The prefix for the whitespace.
    spaces_required_before: The number of spaces required before a token. This
      is a lower-bound for the formatter and not a hard requirement. For
      instance, a comment may have n required spaces before it. But the
      formatter won't place n spaces before all comments. Only those that are
      moved to the end of a line of code. The formatter may use different
      spacing when appropriate.
    can_break_before: True if we're allowed to break before this token.
    must_break_before: True if we're required to break before this token.
    total_length: The total length of the unwrapped line up to and including
      whitespace and this token. However, this doesn't include the initial
      indentation amount.
    split_penalty: The penalty for splitting the line before this token.
  """

  def __init__(self, node):
    """Constructor.

    Arguments:
      node: (pytree.Leaf) The node that's being wrapped.
    """
    self.node = node
    self.next_token = None
    self.previous_token = None
    self.matching_bracket = None
    self.whitespace_prefix = ''
    self.can_break_before = False
    self.must_break_before = False
    self.total_length = 0  # TODO(morbo): Think up a better name.
    self.split_penalty = 0

    if self.is_comment:
      self.spaces_required_before = style.Get('SPACES_BEFORE_COMMENT')
    else:
      self.spaces_required_before = 0

  def AddWhitespacePrefix(self, newlines_before, spaces=0, indent_level=0):
    """Register a token's whitespace prefix.

    This is the whitespace that will be output before a token's string.

    Arguments:
      newlines_before: (int) The number of newlines to place before the token.
      spaces: (int) The number of spaces to place before the token.
      indent_level: (int) The indentation level.
    """
    indent_char = '\t' if style.Get('USE_TABS') else ' '
    indent_before = (
        indent_char * indent_level * style.Get('INDENT_WIDTH') + ' ' * spaces)

    if self.is_comment:
      comment_lines = [s.lstrip() for s in self.value.splitlines()]
      self.node.value = ('\n' + indent_before).join(comment_lines)

    if not self.whitespace_prefix:
      self.whitespace_prefix = (
          '\n' * (self.newlines or newlines_before) + indent_before)
    else:
      self.whitespace_prefix += indent_before

  def AdjustNewlinesBefore(self, newlines_before):
    """Change the number of newlines before this token."""
    self.whitespace_prefix = (
        '\n' * newlines_before + self.whitespace_prefix.lstrip('\n'))

  def RetainHorizontalSpacing(self, first_column, depth):
    """Retains a token's horizontal spacing."""
    previous = self.previous_token
    if previous is None:
      return

    cur_lineno = self.lineno
    prev_lineno = previous.lineno
    if previous.is_multiline_string:
      prev_lineno += previous.value.count('\n')

    if (cur_lineno != prev_lineno or
        (previous.is_pseudo_paren and previous.value != ')' and
         cur_lineno != previous.previous_token.lineno)):
      self.spaces_required_before = (
          self.column - first_column + depth * style.Get('INDENT_WIDTH'))
      return

    cur_column = self.node.column
    prev_column = previous.node.column
    prev_len = len(previous.value)

    if previous.is_pseudo_paren and previous.value == ')':
      prev_column -= 1
      prev_len = 0

    if previous.is_multiline_string:
      prev_len = len(previous.value.split('\n')[-1])
      if '\n' in previous.value:
        prev_column = 0  # Last line starts in column 0.
    self.spaces_required_before = cur_column - (prev_column + prev_len)

  def OpensScope(self):
    return self.value in pytree_utils.OPENING_BRACKETS

  def ClosesScope(self):
    return self.value in pytree_utils.CLOSING_BRACKETS

  def __repr__(self):
    msg = 'FormatToken(name={0}, value={1}'.format(self.name, self.value)
    msg += ', pseudo)' if self.is_pseudo_paren else ')'
    return msg

  @property
  def value(self):
    if self.is_continuation:
      return self.node.value.rstrip()
    return self.node.value

  @property
  @py3compat.lru_cache()
  def node_split_penalty(self):
    """Split penalty attached to the pytree node of this token."""
    return pytree_utils.GetNodeAnnotation(
        self.node, pytree_utils.Annotation.SPLIT_PENALTY, default=0)

  @property
  def newlines(self):
    """The number of newlines needed before this token."""
    return pytree_utils.GetNodeAnnotation(self.node,
                                          pytree_utils.Annotation.NEWLINES)

  @property
  def must_split(self):
    """Return true if the token requires a split before it."""
    return pytree_utils.GetNodeAnnotation(self.node,
                                          pytree_utils.Annotation.MUST_SPLIT)

  @property
  def column(self):
    """The original column number of the node in the source."""
    return self.node.column

  @property
  def lineno(self):
    """The original line number of the node in the source."""
    return self.node.lineno

  @property
  @py3compat.lru_cache()
  def subtypes(self):
    """Extra type information for directing formatting."""
    value = pytree_utils.GetNodeAnnotation(self.node,
                                           pytree_utils.Annotation.SUBTYPE)
    return [Subtype.NONE] if value is None else value

  @property
  @py3compat.lru_cache()
  def is_binary_op(self):
    """Token is a binary operator."""
    return Subtype.BINARY_OPERATOR in self.subtypes

  @property
  @py3compat.lru_cache()
  def name(self):
    """A string representation of the node's name."""
    return pytree_utils.NodeName(self.node)

  @property
  def is_comment(self):
    return self.node.type == token.COMMENT

  @property
  def is_continuation(self):
    return self.node.type == CONTINUATION

  @property
  @py3compat.lru_cache()
  def is_keyword(self):
    return keyword.iskeyword(self.value)

  @property
  @py3compat.lru_cache()
  def is_name(self):
    return self.node.type == token.NAME and not self.is_keyword

  @property
  def is_number(self):
    return self.node.type == token.NUMBER

  @property
  def is_string(self):
    return self.node.type == token.STRING

  @property
  @py3compat.lru_cache()
  def is_multiline_string(self):
    return (self.is_string and
            re.match(r'^[uUbB]?[rR]?(?P<delim>"""|\'\'\').*(?P=delim)$',
                     self.value, re.DOTALL) is not None)

  @property
  @py3compat.lru_cache()
  def is_docstring(self):
    return self.is_multiline_string and not self.node.prev_sibling

  @property
  @py3compat.lru_cache()
  def is_pseudo_paren(self):
    return hasattr(self.node, 'is_pseudo') and self.node.is_pseudo

  @property
  def is_pylint_comment(self):
    return self.is_comment and re.match(r'#\s*\bpylint:\b', self.value)
