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
from yapf.yapflib import pytree_utils
from yapf.yapflib import split_penalty
from yapf.yapflib import style
from yapf.yapflib import unwrapped_line

_COMPOUND_STMTS = frozenset({'for', 'while', 'if', 'elif', 'with', 'except',
                             'def', 'class'})


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
    self.line = line
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
    new.stack = [copy.copy(state) for state in self.stack]
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

    if current.is_pseudo_paren:
      return False

    return current.can_break_before

  def MustSplit(self):
    """Returns True if the line must split before the next token."""
    current = self.next_token
    previous = current.previous_token
    column_limit = style.Get('COLUMN_LIMIT')

    if current.must_break_before:
      return True

    if (previous and (style.Get('DEDENT_CLOSING_BRACKETS') or
                      style.Get('SPLIT_BEFORE_FIRST_ARGUMENT'))):
      bracket = current if current.ClosesScope() else previous
      if format_token.Subtype.SUBSCRIPT_BRACKET not in bracket.subtypes:
        if bracket.OpensScope():
          if style.Get('COALESCE_BRACKETS'):
            if current.OpensScope():
              return False

          if (not _IsLastScopeInLine(bracket) or
              unwrapped_line.IsSurroundedByBrackets(bracket)):
            last_token = bracket.matching_bracket
          else:
            last_token = _LastTokenInLine(bracket.matching_bracket)

          length = last_token.total_length - bracket.total_length
          if length + self.column >= column_limit:
            self.stack[-1].split_before_closing_bracket = True
            return True

        elif style.Get('DEDENT_CLOSING_BRACKETS') and current.ClosesScope():
          return self.stack[-1].split_before_closing_bracket

    if self.stack[-1].split_before_closing_bracket and current.value in '}]':
      # Split if we need to split before the closing bracket.
      return current.node_split_penalty != split_penalty.UNBREAKABLE

    if not previous:
      return False

    # TODO(morbo): This should be controlled with a knob.
    if (format_token.Subtype.DICTIONARY_KEY in current.subtypes and
        not current.is_comment):
      # Place each dictionary entry on its own line.
      return True

    # TODO(morbo): This should be controlled with a knob.
    if format_token.Subtype.DICT_SET_GENERATOR in current.subtypes:
      return True

    if (style.Get('SPLIT_BEFORE_NAMED_ASSIGNS') and
        format_token.Subtype.DEFAULT_OR_NAMED_ASSIGN_ARG_LIST in
        current.subtypes):
      if (previous.value not in {'(', '=', '*', '**'} and
          current.value not in '=,)'):
        opening = _GetOpeningParen(current)
        if opening:
          arglist_length = (opening.matching_bracket.total_length -
                            opening.total_length + self.column)
          return arglist_length > column_limit

    if style.Get('SPLIT_ARGUMENTS_WHEN_COMMA_TERMINATED'):
      # Split before arguments in a function call or definition if the
      # arguments are terminated by a comma.
      opening = _GetOpeningParen(current)
      if opening and opening.previous_token and opening.previous_token.is_name:
        if previous.value in '(,':
          if opening.matching_bracket.previous_token.value == ',':
            return True

    if (previous.value in '{[' and current.lineno != previous.lineno and
        format_token.Subtype.SUBSCRIPT_BRACKET not in previous.subtypes):
      # Retain the split after the container opening.
      return True

    if (previous.value == ':' and _IsDictionaryValue(current) and
        current.lineno != previous.lineno):
      # Retain the split between the dictionary key and value.
      return True

    if (format_token.Subtype.COMP_FOR in current.subtypes and
        format_token.Subtype.COMP_FOR not in previous.subtypes):
      # Split at the beginning of a list comprehension.
      length = _GetLengthOfSubtype(current, format_token.Subtype.COMP_FOR,
                                   format_token.Subtype.COMP_IF)
      if length + self.column > column_limit:
        return True

    if (format_token.Subtype.COMP_IF in current.subtypes and
        format_token.Subtype.COMP_IF not in previous.subtypes):
      # Split at the beginning of an if expression.
      length = _GetLengthOfSubtype(current, format_token.Subtype.COMP_IF)
      if length + self.column > column_limit:
        return True

    previous_previous_token = previous.previous_token
    if (current.is_name and previous_previous_token and
        previous_previous_token.is_name and previous.value == '('):
      sibling = previous.node.next_sibling
      if pytree_utils.NodeName(sibling) == 'arglist':
        arglist = previous.node.next_sibling
        if len(arglist.children) > 2:
          if _IsFunctionCallWithArguments(current):
            # There is a function call, with more than 1 argument, where
            # the first argument is itself a function call with arguments.
            # In this specific case, if we split after the first argument's
            # opening '(', then the formatting will look bad for the rest
            # of the arguments. Instead, enforce a split before that
            # argument to keep things looking good.
            return True
          elif (current.OpensScope() and
                current.matching_bracket.total_length + self.column >
                column_limit):
            # There is a data literal that will need to be split and could mess
            # up the formatting.
            return True

    if (style.Get('SPLIT_BEFORE_BITWISE_OPERATOR') and current.value in '&|' and
        previous.lineno < current.lineno):
      # Retain the split before a bitwise operator.
      return True

    if (current.is_comment and
        previous.lineno < current.lineno - current.value.count('\n')):
      # If a comment comes in the middle of an unwrapped line (like an if
      # conditional with comments interspersed), then we want to split if the
      # original comments were on a separate line.
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
            self.stack[-1].indent - style.Get('CONTINUATION_INDENT_WIDTH'))

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

    if (previous.OpensScope() or (previous.is_comment and
                                  previous.previous_token is not None and
                                  previous.previous_token.OpensScope())):
      self.stack[-1].closing_scope_indent = max(
          0, self.stack[-1].indent - style.Get('CONTINUATION_INDENT_WIDTH'))
      self.stack[-1].split_before_closing_bracket = True

    # Calculate the split penalty.
    penalty = current.split_penalty

    if must_split:
      # Don't penalize for a must split.
      return penalty

    if previous.is_pseudo_paren and previous.value == '(':
      # Small penalty for splitting after a pseudo paren.
      penalty += 50

    # Add a penalty for each increasing newline we add, but don't penalize for
    # splitting before an if-expression or list comprehension.
    if not must_split and current.value not in {'if', 'for'}:
      last = self.stack[-1]
      last.num_line_splits += 1
      penalty += (style.Get('SPLIT_PENALTY_FOR_ADDED_LINE_SPLIT') *
                  last.num_line_splits)

    return penalty + 10

  def _GetNewlineColumn(self):
    """Return the new column on the newline."""
    current = self.next_token
    previous = current.previous_token
    top_of_stack = self.stack[-1]

    if current.spaces_required_before > 2 or self.line.disable:
      return current.spaces_required_before

    if current.OpensScope():
      return top_of_stack.indent if self.paren_level else self.first_indent

    if current.ClosesScope():
      if (previous.OpensScope() or (previous.is_comment and
                                    previous.previous_token is not None and
                                    previous.previous_token.OpensScope())):
        return max(0,
                   top_of_stack.indent - style.Get('CONTINUATION_INDENT_WIDTH'))
      return top_of_stack.closing_scope_indent

    if (previous and previous.is_string and current.is_string and
        format_token.Subtype.DICTIONARY_VALUE in current.subtypes):
      return previous.column

    if style.Get('INDENT_DICTIONARY_VALUE'):
      if previous and (previous.value == ':' or previous.is_pseudo_paren):
        if format_token.Subtype.DICTIONARY_VALUE in current.subtypes:
          return top_of_stack.indent

    if (self.line.first.value in _COMPOUND_STMTS and
        (not style.Get('DEDENT_CLOSING_BRACKETS') or
         style.Get('SPLIT_BEFORE_FIRST_ARGUMENT'))):
      token_indent = (len(self.line.first.whitespace_prefix.split('\n')[-1]) +
                      style.Get('INDENT_WIDTH'))
      if token_indent == top_of_stack.indent:
        return top_of_stack.indent + style.Get('CONTINUATION_INDENT_WIDTH')

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
    elif not current.is_pseudo_paren or current.value == '(':
      self.column += len(current.value)

    self.next_token = self.next_token.next_token

    # Calculate the penalty for overflowing the column limit.
    penalty = 0
    if self.column > style.Get('COLUMN_LIMIT'):
      excess_characters = self.column - style.Get('COLUMN_LIMIT')
      penalty += style.Get('SPLIT_PENALTY_EXCESS_CHARACTER') * excess_characters

    if is_multiline_string:
      # If this is a multiline string, the column is actually the
      # end of the last line in the string.
      self.column = len(current.value.split('\n')[-1])

    return penalty


def _IsFunctionCallWithArguments(token):
  while token:
    if token.value == '(':
      token = token.next_token
      return token and token.value != ')'
    elif token.name not in {'NAME', 'DOT'}:
      break
    token = token.next_token
  return False


def _IsDictionaryValue(token):
  while token:
    if format_token.Subtype.DICTIONARY_VALUE in token.subtypes:
      return True
    token = token.previous_token
  return False


def _GetLengthOfSubtype(token, subtype, exclude=None):
  current = token
  while (current.next_token and subtype in current.subtypes and
         (exclude is None or exclude not in current.subtypes)):
    current = current.next_token
  return current.total_length - token.total_length + 1


def _GetOpeningParen(current):
  previous = current
  if previous and previous.matching_bracket:
    return previous.matching_bracket
  while previous is not None and previous.matching_bracket is None:
    previous = previous.previous_token
    if not previous:
      break
    if previous.ClosesScope():
      previous = previous.matching_bracket.previous_token
  return previous


def _LastTokenInLine(current):
  while not current.is_comment and current.next_token:
    current = current.next_token
  return current


def _IsLastScopeInLine(current):
  while current:
    current = current.next_token
    if current and current.OpensScope():
      return False
  return True


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
    num_line_splits: Number of line splits this _ParenState contains already.
      Each subsequent line split gets an increasing penalty.
  """

  # TODO(morbo): This doesn't track "bin packing."

  def __init__(self, indent, last_space):
    self.indent = indent
    self.last_space = last_space
    self.closing_scope_indent = 0
    self.split_before_closing_bracket = False
    self.num_line_splits = 0

  def __copy__(self):
    state = _ParenState(self.indent, self.last_space)
    state.closing_scope_indent = self.closing_scope_indent
    state.split_before_closing_bracket = self.split_before_closing_bracket
    state.num_line_splits = self.num_line_splits
    return state

  def __repr__(self):
    return '[indent::%d, last_space::%d, closing_scope_indent::%d]' % (
        self.indent, self.last_space, self.closing_scope_indent)
