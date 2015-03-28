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
"""Decide what the format for the code should be.

The `unwrapped_line.UnwrappedLine`s are now ready to be formatted.
UnwrappedLines that can be merged together are. The best formatting is returned
as a string.

  Reformat(): the main function exported by this module.
"""

import __future__
import tokenize
import collections
import heapq
import re

try:
  from StringIO import StringIO
except ImportError:
  from io import StringIO
from yapf.yapflib import format_decision_state
from yapf.yapflib import line_joiner
from yapf.yapflib import pytree_utils
from yapf.yapflib import style
from yapf.yapflib import verifier


def Reformat(uwlines, unformatted_source=None):
  """Reformat the unwrapped lines.

  Arguments:
    uwlines: (list of unwrapped_line.UnwrappedLine) Lines we want to format.

  Returns:
    A string representing the reformatted code.
  """
  final_lines = []
  prev_last_uwline = None  # The previous line.
  compile_flags = _ExtractFutureImports(unformatted_source) \
                  if unformatted_source else 0

  for uwline in _SingleOrMergedLines(uwlines):
    first_token = uwline.first
    _FormatFirstToken(first_token, uwline.depth, prev_last_uwline)

    indent_amt = style.Get('INDENT_WIDTH') * uwline.depth
    state = format_decision_state.FormatDecisionState(uwline, indent_amt)
    if _LineContainsI18n(uwline):
      _EmitLineUnformatted(state)
    elif _CanPlaceOnSingleLine(uwline):
      # The unwrapped line fits on one line.
      while state.next_token:
        state.AddTokenToState(newline=False, dry_run=False)
    else:
      _AnalyzeSolutionSpace(state, dry_run=False)

    final_lines.append(uwline)
    prev_last_uwline = uwline

  formatted_code = []
  for line in final_lines:
    formatted_line = []
    for token in line.tokens:
      if token.name in pytree_utils.NONSEMANTIC_TOKENS:
        continue
      formatted_line.append(token.whitespace_prefix)
      formatted_line.append(token.value)
    formatted_code.append(''.join(formatted_line))
    verifier.VerifyCode(formatted_code[-1], compile_flags=compile_flags)

  return ''.join(formatted_code) + '\n'


def _EmitLineUnformatted(state):
  """Emit the line without formatting.

  The line contains code that if reformatted would break a non-syntactic
  convention. E.g., i18n comments and function calls are tightly bound by
  convention. Instead, we calculate when / if a newline should occur and honor
  that. But otherwise the code emitted will be the same as the original code.

  Arguments:
    state: (format_decision_state.FormatDecisionState) The format decision
      state.
  """
  prev_lineno = None
  while state.next_token:
    newline = (prev_lineno is not None and
               state.next_token.lineno > state.next_token.previous_token.lineno)
    prev_lineno = state.next_token.lineno
    state.AddTokenToState(newline=newline, dry_run=False)


def _LineContainsI18n(uwline):
  """Return true if there are i18n comments or function calls in the line.

  I18n comments and pseudo-function calls are closely related. They cannot
  be moved apart without breaking i18n.

  Arguments:
    uwline: (unwrapped_line.UnwrappedLine) The line currently being formatted.

  Returns:
    True if the line contains i18n comments or function calls. False otherwise.
  """
  if (style.Get('I18N_COMMENT') and any(re.search(style.Get('I18N_COMMENT'),
                                                  token.value)
                                        for token in uwline.tokens)):
    # Contains an i18n comment.
    return True

  if style.Get('I18N_FUNCTION_CALL'):
    length = len(uwline.tokens)
    index = 0
    while index < length - 1:
      if (uwline.tokens[index + 1].value == '(' and
          uwline.tokens[index].value in style.Get('I18N_FUNCTION_CALL')):
        return True
      index += 1

  return False


def _CanPlaceOnSingleLine(uwline):
  """Determine if the unwrapped line can go on a single line.

  Arguments:
    uwline: (unwrapped_line.UnwrappedLine) The line currently being formatted.

  Returns:
    True if the line can or should be added to a single line. False otherwise.
  """
  indent_amt = style.Get('INDENT_WIDTH') * uwline.depth
  return (uwline.last.total_length + indent_amt <= style.Get('COLUMN_LIMIT') and
          not any(token.is_comment for token in uwline.tokens[:-1]))


class _StateNode(object):
  """An edge in the solution space from 'previous.state' to 'state'.

  Attributes:
    state: (format_decision_state.FormatDecisionState) The format decision state
      for this node.
    newline: If True, then on the edge from 'previous.state' to 'state' a
      newline is inserted.
    previous: (_StateNode) The previous state node in the graph.
  """

  # TODO(morbo): Add a '__cmp__' method.

  def __init__(self, state, newline, previous):
    self.state = state.Clone()
    self.newline = newline
    self.previous = previous

  def __repr__(self):
    return 'StateNode(state=[\n{0}\n], newline={1})'.format(self.state,
                                                            self.newline)

# A tuple of (penalty, count) that is used to prioritize the BFS. In case of
# equal penalties, we prefer states that were inserted first. During state
# generation, we make sure that we insert states first that break the line as
# late as possible.
_OrderedPenalty = collections.namedtuple('OrderedPenalty', ['penalty', 'count'])

# An item in the prioritized BFS search queue. The 'StateNode's 'state' has
# the given '_OrderedPenalty'.
_QueueItem = collections.namedtuple('QueueItem', ['ordered_penalty',
                                                  'state_node'])


def _AnalyzeSolutionSpace(initial_state, dry_run=False):
  """Analyze the entire solution space starting from initial_state.

  This implements a variant of Dijkstra's algorithm on the graph that spans
  the solution space (LineStates are the nodes). The algorithm tries to find
  the shortest path (the one with the lowest penalty) from 'initial_state' to
  the state where all tokens are placed.

  Arguments:
    initial_state: (format_decision_state.FormatDecisionState) The initial state
      to start the search from.
    dry_run: (bool) Don't commit changes if True.
  """
  count = 0
  seen = set()
  p_queue = []

  # Insert start element.
  node = _StateNode(initial_state, False, None)
  heapq.heappush(p_queue, _QueueItem(_OrderedPenalty(0, count), node))

  count += 1
  prev_penalty = 0
  while p_queue:
    item = p_queue[0]
    penalty = item.ordered_penalty.penalty
    node = item.state_node
    if not node.state.next_token:
      break
    heapq.heappop(p_queue)

    if count > 10000:
      node.state.ignore_stack_for_comparison = True

    if node.state in seen:
      continue

    assert penalty >= prev_penalty
    prev_penalty = penalty

    seen.add(node.state)

    # FIXME(morbo): Add a 'decision' element?

    count = _AddNextStateToQueue(penalty, node, False, count, p_queue)
    count = _AddNextStateToQueue(penalty, node, True, count, p_queue)

  if not p_queue:
    # We weren't able to find a solution. Do nothing.
    return

  if not dry_run:
    _ReconstructPath(initial_state, heapq.heappop(p_queue).state_node)


def _AddNextStateToQueue(penalty, previous_node, newline, count, p_queue):
  """Add the following state to the analysis queue.

  Assume the current state is 'previous_node' and has been reached with a
  penalty of 'penalty'. Insert a line break if 'newline' is True.

  Arguments:
    penalty: (int) The penalty associated with the path up to this point.
    previous_node: (_StateNode) The last _StateNode inserted into the priority
      queue.
    newline: (bool) Add a newline if True.
    count: (int) The number of elements in the queue.
    p_queue: (heapq) The priority queue representing the solution space.

  Returns:
    The updated number of elements in the queue.
  """
  if newline and not previous_node.state.CanSplit():
    # Don't add a newline if the token cannot be split.
    return count
  if not newline and previous_node.state.MustSplit():
    # Don't add a token we must split but where we aren't splitting.
    return count

  if previous_node.state.next_token.value in pytree_utils.CLOSING_BRACKETS:
    if _MatchingParenSplitDecision(previous_node) != newline:
      penalty += style.Get('SPLIT_PENALTY_MATCHING_BRACKET')

  node = _StateNode(previous_node.state, newline, previous_node)
  penalty += node.state.AddTokenToState(newline=newline, dry_run=True)
  heapq.heappush(p_queue, _QueueItem(_OrderedPenalty(penalty, count), node))
  return count + 1


def _ReconstructPath(initial_state, current):
  """Reconstruct the path through the queue with lowest penalty.

  Arguments:
    initial_state: (format_decision_state.FormatDecisionState) The initial state
      to start the search from.
    current: (_StateNode) The node in the decision graph that is the end point
      of the path with the least penalty.
  """
  path = collections.deque()

  while current.previous:
    path.appendleft(current)
    current = current.previous

  for node in path:
    initial_state.AddTokenToState(newline=node.newline, dry_run=False)


def _MatchingParenSplitDecision(current):
  """Returns the splitting decision of the matching token.

  Arguments:
    current: (_StateNode) The node in the decision graph that is the end point
      of the path with the least penalty.

  Returns:
    True if the matching paren split after it, False otherwise.
  """
  # FIXME(morbo): This is not ideal, because it backtracks through code.
  # In the general case, it shouldn't be too bad, but it is technically
  # O(n^2) behavior, which is never good.
  matching_bracket = current.state.next_token.matching_bracket
  newline = current.newline
  while current.previous:
    if current.state.next_token.previous_token == matching_bracket:
      break
    newline = current.newline
    current = current.previous
  return newline or current.state.next_token.is_comment


def _FormatFirstToken(first_token, indent_depth, prev_last_uwline):
  """Format the first token in the unwrapped line.

  Add a newline and the required indent before the first token of the unwrapped
  line.

  Arguments:
    first_token: (format_token.FormatToken) The first token in the unwrapped
      line.
    indent_depth: (int) The line's indentation depth.
    prev_last_uwline: (list of unwrapped_line.UnwrappedLine) The unwrapped line
      previous to this line.
  """
  first_token.AddWhitespacePrefix(_CalculateNumberOfNewlines(first_token,
                                                             indent_depth,
                                                             prev_last_uwline),
                                  indent_level=indent_depth)


NO_BLANK_LINES = 1
ONE_BLANK_LINE = 2
TWO_BLANK_LINES = 3


def _CalculateNumberOfNewlines(first_token, indent_depth, prev_last_uwline):
  """Calculate the number of newlines we need to add.

  Arguments:
    first_token: (format_token.FormatToken) The first token in the unwrapped
      line.
    indent_depth: (int) The line's indentation depth.
    prev_last_uwline: (list of unwrapped_line.UnwrappedLine) The unwrapped line
      previous to this line.

  Returns:
    The number of newlines needed before the first token.
  """
  # TODO(morbo): Special handling for imports.
  # TODO(morbo): Create a knob that can tune these.
  if prev_last_uwline is None:
    # The first line in the file. Don't add blank lines.
    # FIXME(morbo): Is this correct?
    if first_token.newlines is not None:
      pytree_utils.SetNodeAnnotation(first_token.GetPytreeNode(),
                                     pytree_utils.Annotation.NEWLINES, None)
    return 0

  if first_token.is_docstring:
    # The docstring shouldn't have a newline before it.
    # TODO(morbo): Add a knob to adjust this.
    return NO_BLANK_LINES

  prev_last_token = prev_last_uwline.last
  if prev_last_token.is_docstring:
    if not indent_depth and first_token.value in {'class', 'def'}:
      # Separate a class or function from the module-level docstring with two
      # blank lines.
      return TWO_BLANK_LINES
    if _NoBlankLinesBeforeCurrentToken(prev_last_token.value, first_token,
                                       prev_last_token):
      return NO_BLANK_LINES
    else:
      return ONE_BLANK_LINE

  if first_token.value in {'class', 'def'}:
    # TODO(morbo): This can go once the blank line calculator is more
    # sophisticated.
    if not indent_depth:
      # This is a top-level class or function.
      is_inline_comment = prev_last_token.whitespace_prefix.count('\n') == 0
      if prev_last_token.is_comment and not is_inline_comment:
        # This token follows a non-inline comment.
        if _NoBlankLinesBeforeCurrentToken(prev_last_token.value, first_token,
                                           prev_last_token):
          # Assume that the comment is "attached" to the current line.
          # Therefore, we want two blank lines before the comment.
          prev_last_token.AdjustNewlinesBefore(TWO_BLANK_LINES)
          if first_token.newlines is not None:
            pytree_utils.SetNodeAnnotation(first_token.GetPytreeNode(),
                                           pytree_utils.Annotation.NEWLINES,
                                           None)
          return NO_BLANK_LINES
    elif prev_last_uwline.first.value in {'class', 'def'}:
      if not style.Get('BLANK_LINE_BEFORE_NESTED_CLASS_OR_DEF'):
        pytree_utils.SetNodeAnnotation(first_token.node,
                                       pytree_utils.Annotation.NEWLINES, None)
        return NO_BLANK_LINES

  # Calculate how many newlines were between the original lines. We want to
  # retain that formatting if it doesn't violate one of the style guide rules.
  if first_token.is_comment:
    first_token_lineno = first_token.lineno - first_token.value.count('\n')
  else:
    first_token_lineno = first_token.lineno

  if first_token_lineno - prev_last_token.lineno > 1:
    return ONE_BLANK_LINE
  else:
    return NO_BLANK_LINES


def _SingleOrMergedLines(uwlines):
  """Generate the lines we want to format.

  Arguments:
    uwlines: (list of unwrapped_line.UnwrappedLine) Lines we want to format.

  Yields:
    Either a single line, if the current line cannot be merged with the
    succeeding line, or the next two lines merged into one line.
  """
  index = 0
  last_was_merged = False
  while index < len(uwlines):
    # TODO(morbo): This splice is potentially very slow. Come up with a more
    # performance-friendly way of determining if two lines can be merged.
    if line_joiner.CanMergeMultipleLines(uwlines[index:], last_was_merged):
      for token in uwlines[index + 1].tokens:
        uwlines[index].AppendToken(token)
      yield uwlines[index]
      index += 2
      last_was_merged = True
    else:
      yield uwlines[index]
      index += 1
      last_was_merged = False


def _NoBlankLinesBeforeCurrentToken(text, cur_token, prev_token):
  """Determine if there are no blank lines before the current token.

  The previous token is a docstring or comment. The prev_token_lineno is the
  start of the text of that token. Counting the number of newlines in its text
  gives us the extent and thus where the line number of the end of the
  docstring or comment. After that, we just compare it to the current token's
  line number to see if there are blank lines between them.

  Arguments:
    text: (unicode) The text of the docstring or comment before the current
      token.
    cur_token: (format_token.FormatToken) The current token in the unwrapped
      line.
    prev_token: (format_token.FormatToken) The previous token in the unwrapped
      line.

  Returns:
    True if there is no blank line before the current token.
  """
  cur_token_lineno = cur_token.lineno
  if cur_token.is_comment:
    cur_token_lineno -= cur_token.value.count('\n')
  num_newlines = text.count('\n') if not prev_token.is_comment else 0
  return prev_token.lineno + num_newlines == cur_token_lineno - 1


def _ExtractFutureImports(unformatted_source):
  """
  Establish which features have been imported from __future__
  and return an integer value suitable for use in the compile()
  'flags' parameter.
  """
  def get_all_imports(tokens, last_was_name=False):
    """
    Pop tokens until we get to a NAME type, then if it's an import
    return it and recurse. If it's a newline or endmarker, end the
    recursion. last_was_name makes sure that NAME tokens adjacent to
    one another don't get returned, such as the 'as' and 'print2' tokens
    in "print_function as print2".
    """
    while True:
      t = next(tokens)
      if t[0] == tokenize.NAME:
        if not last_was_name:
          return [t[1]] + get_all_imports(tokens, True)
      elif t[0] in (tokenize.NEWLINE, tokenize.ENDMARKER):
        return []
      else:
        last_was_name = False

  flags = 0
  tokens = tokenize.generate_tokens(
    StringIO(unformatted_source).readline)
  imports = []
  try:
    while True:
      # from __future__ import has to be the first statement in a file
      # https://docs.python.org/2/reference/simple_stmts.html#future
      first_three_tokens = " ".join(
        (next(tokens)[1], next(tokens)[1], next(tokens)[1]))
      if first_three_tokens == "from __future__ import":
        imports += get_all_imports(tokens)
      else:
        # Keep popping tokens until the end of the _logical_ line
        # https://docs.python.org/2/library/tokenize.html#tokenize.NL
        while True:
          t = next(tokens)
          if t[0] in (tokenize.NEWLINE, tokenize.ENDMARKER):
            break
  except StopIteration:
    # We reached the end of the file
    pass

  for imp in imports:
    if imp in __future__.all_feature_names:
      flags |= getattr(__future__, imp).compiler_flag
  return flags
