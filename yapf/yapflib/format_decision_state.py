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
"""Implements a format decision state object that manages whitespace decisions.

Each token is processed one at a time, at which point its whitespace formatting
decisions are made. A graph of potential whitespace formattings is created,
where each node in the graph is a format decision state object. The heuristic
tries formatting the token with and without a newline before it to determine
which one has the least penalty. Therefore, the format decision state object for
each decision needs to be its own unique copy.

Once the heuristic determines the best formatting, it makes a non-dry run pass
through the code to commit the whitespace formatting.

  FormatDecisionState: main class exported by this module.
"""

import copy

from yapf.yapflib import format_token
from yapf.yapflib import style


class FormatDecisionState(object):
  """The current state when indenting an unwrapped line.

  The FormatDecisionState object is meant to be copied instead of referenced.

  Attributes:
    first_indent: The indent of the first token.
    column: The number of used columns in the current line.
    next_token: The next token to be formatted.
    paren_level: The level of nesting inside (), [], and {}.
    start_of_line_level: The paren_level at the start of this line.
    lowest_level_on_line: The lowest paren_level on the current line.
    newline: Indicates if a newline is added along the edge to this format
      decision state node.
    previous: The previous format decision state in the decision tree.
    stack: A stack (of _ParenState) keeping track of properties applying to
      parenthesis levels.
    ignore_stack_for_comparison: Ignore the stack of _ParenState for state
      comparison.
  """

  def __init__(self, line, first_indent):
    """Initializer.

    Initializes to the state after placing the first token from 'line' at
    'first_indent'.

    Arguments:
      line: (UnwrappedLine) The unwrapped line we're currently processing.
      first_indent: (int) The indent of the first token.
    """
    self.next_token = line.first
    self.column = first_indent
    self.paren_level = 0
    self.start_of_line_level = 0
    self.lowest_level_on_line = 0
    self.ignore_stack_for_comparison = False
    self.stack = [_ParenState(first_indent, first_indent)]
    self.first_indent = first_indent
    self.newline = False
    self.previous = None
    self._MoveStateToNextToken()

  def Clone(self):
    new = copy.copy(self)
    new.stack = copy.deepcopy(self.stack)
    return new

  def __eq__(self, other):
    # Note: 'first_indent' is implicit in the stack. Also, we ignore 'previous',
    # because it shouldn't have a bearing on this comparison. (I.e., it will
    # report equal if 'next_token' does.)
    return (self.next_token == other.next_token and
            self.column == other.column and
            self.paren_level == other.paren_level and
            self.start_of_line_level == other.start_of_line_level and
            self.lowest_level_on_line == other.lowest_level_on_line and
            (self.ignore_stack_for_comparison or
             other.ignore_stack_for_comparison or self.stack == other.stack))

  def __ne__(self, other):
    return not self == other

  def __hash__(self):
    return hash((self.next_token, self.column, self.paren_level,
                 self.start_of_line_level, self.lowest_level_on_line))

  def __repr__(self):
    return ('column::%d, next_token::%s, paren_level::%d, stack::[\n\t%s' %
            (self.column, repr(self.next_token), self.paren_level,
             '\n\t'.join(repr(s) for s in self.stack) + ']'))

  def CanSplit(self):
    """Returns True if the line can be split before the next token."""
    current = self.next_token

    if not current.can_break_before:
      return False

    return True

  def MustSplit(self):
    """Returns True if the line must split before the next token."""
    current = self.next_token
    previous_token = current.previous_token

    if current.must_break_before:
      return True

    if (self.stack[-1].split_before_closing_bracket and
        # FIXME(morbo): Use the 'matching_bracket' instead of this.
        # FIXME(morbo): Don't forget about tuples!
        current.value in ']}'):
      # Split if we need to split before the closing bracket and the next
      # token is a closing bracket.
      return True

    if previous_token:
      length = _GetLengthToMatchingParen(previous_token)
      if (previous_token.value == '{' and  # TODO(morbo): List initializers?
          length + self.column > style.Get('COLUMN_LIMIT')):
        return True

      # TODO(morbo): This should be controlled with a knob.
      if (format_token.Subtype.DICTIONARY_KEY in current.subtypes and
          not current.is_comment):
        # Place each dictionary entry on its own line.
        return True

      # TODO(morbo): This should be controlled with a knob.
      if format_token.Subtype.DICT_SET_GENERATOR in current.subtypes:
        return True

      if (previous_token.value not in '(=' and current.value not in '=,)' and
          format_token.Subtype.DEFAULT_OR_NAMED_ASSIGN_ARG_LIST in
          current.subtypes):
        return style.Get('SPLIT_BEFORE_NAMED_ASSIGNS')

      if (previous_token.value in '{[(' and
          current.lineno != previous_token.lineno):
        self.stack[-1].split_before_closing_bracket = True
        return True

    return False

  def AddTokenToState(self, newline, dry_run, must_split=False):
    """Add a token to the format decision state.

    Allow the heuristic to try out adding the token with and without a newline.
    Later on, the algorithm will determine which one has the lowest penalty.

    Arguments:
      newline: (bool) Add the token on a new line if True.
      dry_run: (bool) Don't commit whitespace changes to the FormatToken if
        True.
      must_split: (bool) A newline was required before this token.

    Returns:
      The penalty of splitting after the current token.
    """
    penalty = 0
    if newline:
      penalty = self._AddTokenOnNewline(dry_run, must_split)
    else:
      self._AddTokenOnCurrentLine(dry_run)

    return self._MoveStateToNextToken() + penalty

  def _AddTokenOnCurrentLine(self, dry_run):
    """Puts the token on the current line.

    Appends the next token to the state and updates information necessary for
    indentation.

    Arguments:
      dry_run: (bool) Commit whitespace changes to the FormatToken if True.
    """
    current = self.next_token
    previous = current.previous_token

    spaces = current.spaces_required_before
    if not dry_run:
      current.AddWhitespacePrefix(newlines_before=0, spaces=spaces)

    if previous.OpensScope():
      if not current.is_comment:
        # Align closing scopes that are on a newline with the opening scope:
        #
        #     foo = [a,
        #            b,
        #           ]
        self.stack[-1].closing_scope_indent = self.column - 1
        if style.Get('ALIGN_CLOSING_BRACKET_WITH_VISUAL_INDENT'):
          self.stack[-1].closing_scope_indent += 1
        self.stack[-1].indent = self.column + spaces
      else:
        self.stack[-1].closing_scope_indent = (
            self.stack[-1].indent - style.Get('CONTINUATION_INDENT_WIDTH')
        )

    self.column += spaces

  def _AddTokenOnNewline(self, dry_run, must_split):
    """Adds a line break and necessary indentation.

    Appends the next token to the state and updates information necessary for
    indentation.

    Arguments:
      dry_run: (bool) Don't commit whitespace changes to the FormatToken if
        True.
      must_split: (bool) A newline was required before this token.

    Returns:
      The split penalty for splitting after the current state.
    """
    current = self.next_token
    previous = current.previous_token

    self.column = self._GetNewlineColumn()

    if not dry_run:
      current.AddWhitespacePrefix(newlines_before=1, spaces=self.column)

    if not current.is_comment:
      self.stack[-1].last_space = self.column
    self.start_of_line_level = self.paren_level
    self.lowest_level_on_line = self.paren_level

    # Any break on this level means that the parent level has been broken and we
    # need to avoid bin packing there.
    for paren_state in self.stack:
      paren_state.split_before_parameter = True

    if (previous.value != ',' and not previous.is_binary_op and
        not current.is_binary_op and not previous.OpensScope()):
      self.stack[-1].split_before_parameter = True

    if (previous.OpensScope() or
        (previous.is_comment and previous.previous_token is not None and
         previous.previous_token.OpensScope())):
      self.stack[-1].closing_scope_indent = max(
          0, self.stack[-1].indent - style.Get('CONTINUATION_INDENT_WIDTH'))
      self.stack[-1].split_before_closing_bracket = True

    # Calculate the split penalty.
    penalty = current.split_penalty

    # Add a penalty for each increasing newline we add.
    last = self.stack[-1]
    penalty += (
        style.Get('SPLIT_PENALTY_FOR_ADDED_LINE_SPLIT') * last.num_line_splits
    )
    if not must_split and current.value not in {'if', 'for'}:
      # Don't penalize for a must split or for splitting before an
      # if-expression or list comprehension.
      last.num_line_splits += 1

    return penalty + 10

  def _GetNewlineColumn(self):
    """Return the new column on the newline."""
    current = self.next_token
    previous = current.previous_token
    top_of_stack = self.stack[-1]

    if current.spaces_required_before > 2:
      return current.spaces_required_before

    if current.OpensScope():
      return self.first_indent if not self.paren_level else top_of_stack.indent

    if current.ClosesScope():
      if (previous.OpensScope() or
          (previous.is_comment and previous.previous_token is not None and
           previous.previous_token.OpensScope())):
        return max(
            0, self.stack[-1].indent - style.Get('CONTINUATION_INDENT_WIDTH'))
      return top_of_stack.closing_scope_indent

    if (previous and previous.is_string and current.is_string and
        format_token.Subtype.DICTIONARY_VALUE in current.subtypes):
      return previous.column

    if format_token.Subtype.IF_TEST_EXPR in current.subtypes:
      return top_of_stack.indent + style.Get('INDENT_IF_EXPR_CONTINUATION')

    return top_of_stack.indent

  def _MoveStateToNextToken(self):
    """Calculate format decision state information and move onto the next token.

    Before moving onto the next token, we first calculate the format decision
    state given the current token and its formatting decisions. Then the format
    decision state is set up so that the next token can be added.

    Returns:
      The penalty for the number of characters over the column limit.
    """
    current = self.next_token
    if not current.OpensScope() and not current.ClosesScope():
      self.lowest_level_on_line = min(self.lowest_level_on_line,
                                      self.paren_level)

    # If we encounter an opening bracket, we add a level to our stack to prepare
    # for the subsequent tokens.
    if current.OpensScope():
      last = self.stack[-1]
      new_indent = style.Get('CONTINUATION_INDENT_WIDTH') + last.last_space

      self.stack.append(_ParenState(new_indent, self.stack[-1].last_space))
      self.stack[-1].break_before_paremeter = False
      self.paren_level += 1

    # If we encounter a closing bracket, we can remove a level from our
    # parenthesis stack.
    if len(self.stack) > 1 and current.ClosesScope():
      self.stack[-2].last_space = self.stack[-1].last_space
      self.stack.pop()
      self.paren_level -= 1

    is_multiline_string = current.is_string and '\n' in current.value
    if is_multiline_string:
      # This is a multiline string. Only look at the first line.
      self.column += len(current.value.split('\n')[0])
    else:
      self.column += len(current.value)

    self.next_token = self.next_token.next_token

    # Calculate the penalty for overflowing the column limit.
    penalty = 0
    if self.column > style.Get('COLUMN_LIMIT') and not current.is_comment:
      excess_characters = self.column - style.Get('COLUMN_LIMIT')
      penalty = style.Get('SPLIT_PENALTY_EXCESS_CHARACTER') * excess_characters

    if is_multiline_string:
      # If this is a multiline string, the column is actually the
      # end of the last line in the string.
      self.column = len(current.value.split('\n')[-1])

    return penalty


def _GetLengthToMatchingParen(token):
  """Returns the length from one bracket to the matching bracket.

  Arguments:
    token: (FormatToken) The opening bracket token.

  Returns:
    The length to the closing paren or up to the first point where we can split
    the line. The length includes the brackets.
  """
  if not token.matching_bracket:
    return 0
  end = token.matching_bracket
  while end.next_token and not end.next_token.can_break_before:
    end = end.next_token
  return end.total_length - token.total_length + 1


class _ParenState(object):
  """Maintains the state of the bracket enclosures.

  A stack of _ParenState objects are kept so that we know how to indent relative
  to the brackets.

  Attributes:
    indent: The column position to which a specified parenthesis level needs to
      be indented.
    last_space: The column position of the last space on each level.
    split_before_closing_bracket: Whether a newline needs to be inserted before
      the closing bracket. We only want to insert a newline before the closing
      bracket if there also was a newline after the beginning left bracket.
    split_before_parameter: Split the line after the next comma.
    num_line_splits: Number of line splits this _ParenState contains already.
      Each subsequent line split gets an increasing penalty.
  """

  # TODO(morbo): This doesn't track "bin packing."

  def __init__(self, indent, last_space):
    self.indent = indent
    self.last_space = last_space
    self.closing_scope_indent = 0
    self.split_before_closing_bracket = False
    self.split_before_parameter = False
    self.num_line_splits = 0

  def __repr__(self):
    return '[indent::%d, last_space::%d, closing_scope_indent::%d]' % (
        self.indent, self.last_space, self.closing_scope_indent)
