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
"""LayoutUnwrapper - produces a list of logical lines from a tree.

[for a description of what a logical line is, see logical_line.py]

This is a layout tree visitor that goes over a parse tree and produces a list of
LogicalLine containers from it, each with its own depth and containing all the
tokens that could fit on the line if there were no maximal line-length
limitations.

Note: a precondition to running this visitor and obtaining correct results is
for the tree to have its comments spliced in as nodes. Prefixes are ignored.

For most uses, the convenience function Unwrap should be sufficient.
"""

# Distinguish token categories from the tokens being unwrapped.
from yapf.layout import split_penalty
from yapf.layout import tokens as layout_token
from yapf.layout import tree as layout_tree
from yapf.layout import utils
from yapf.layout import visitor
from yapf.yapflib import format_token
from yapf.yapflib import logical_line
from yapf.yapflib import object_state
from yapf.yapflib import style
from yapf.yapflib import subtypes

_OPENING_BRACKETS = frozenset({'(', '[', '{'})
_CLOSING_BRACKETS = frozenset({')', ']', '}'})


def Unwrap(tree):
  """Create and return a list of logical lines from the given tree.

  Arguments:
    tree: the top-level layout tree node to unwrap..

  Returns:
    A list of LogicalLine objects.
  """
  unwrapper = LayoutUnwrapper()
  unwrapper.Visit(tree)
  llines = unwrapper.GetLogicalLines()
  llines.sort(key=lambda x: x.lineno)
  return llines


# Grammar tokens considered as whitespace for the purpose of unwrapping.
_WHITESPACE_TOKENS = frozenset([
    layout_token.NEWLINE, layout_token.DEDENT, layout_token.INDENT,
    layout_token.ENDMARKER
])


class LayoutUnwrapper(visitor.LayoutVisitor):
  """LayoutUnwrapper - see file-level docstring for detailed description.

  Visiting a layout group emits its tokens into depth-tagged logical lines.
  """

  def __init__(self):
    # A list of all logical lines finished visiting so far.
    self._logical_lines = []

    # Builds up a current logical line while visiting layout nodes. Some nodes
    # will finish a line and start a new one.
    self._cur_logical_line = logical_line.LogicalLine(0)

    # Current indentation depth.
    self._cur_depth = 0

  def GetLogicalLines(self):
    """Fetch the result of the tree walk.

    Note: only call this after visiting the whole tree.

    Returns:
      A list of LogicalLine objects.
    """
    # Make sure the last line that was being populated is flushed.
    self._StartNewLine()
    return self._logical_lines

  def _StartNewLine(self):
    """Finish current line and start a new one.

    Place the currently accumulated line into the _logical_lines list and
    start a new one.
    """
    if self._cur_logical_line.tokens:
      self._logical_lines.append(self._cur_logical_line)
      _MatchBrackets(self._cur_logical_line)
      _IdentifyParameterLists(self._cur_logical_line)
      _AdjustSplitPenalty(self._cur_logical_line)
    self._cur_logical_line = logical_line.LogicalLine(self._cur_depth)

  _STMT_TYPES = frozenset({
      'if_stmt',
      'while_stmt',
      'for_stmt',
      'try_stmt',
      'expect_clause',
      'with_stmt',
      'match_stmt',
      'case_block',
      'funcdef',
      'classdef',
  })

  # pylint: disable=invalid-name,missing-docstring
  def Visit_simple_stmt(self, node):
    # A 'simple_stmt' conveniently represents a non-compound Python statement,
    # i.e. a statement that does not contain other statements.

    # When compound nodes have a single statement as their suite, the parser
    # can leave it in the tree directly without creating a suite. But we have
    # to increase depth in these cases as well. However, don't increase the
    # depth of we have a simple_stmt that's a comment node. This represents a
    # standalone comment and in the case of it coming directly after the
    # funcdef, it is a "top" comment for the whole function.
    # TODO(eliben): add more relevant compound statements here.
    single_stmt_suite = (
        node.parent and utils.NodeName(node.parent) in self._STMT_TYPES)
    is_comment_stmt = utils.IsCommentStatement(node)
    is_inside_match = node.parent and utils.NodeName(
        node.parent) == 'match_stmt'
    if (single_stmt_suite and not is_comment_stmt) or is_inside_match:
      self._cur_depth += 1
    self._StartNewLine()
    self.DefaultNodeVisit(node)
    if (single_stmt_suite and not is_comment_stmt) or is_inside_match:
      self._cur_depth -= 1

  def _VisitCompoundStatement(self, node, substatement_names):
    """Helper for visiting compound statements.

    Python compound statements serve as containers for other statements. Thus,
    when we encounter a new compound statement, we start a new logical line.

    Arguments:
      node: the node to visit.
      substatement_names: set of node names. A compound statement will be
        recognized as a NAME node with a name in this set.
    """
    for child in node.children:
      # A single 'if_stmt' layout group contains the entire conditional,
      # including 'if', 'elif' and 'else' nodes as children (similar
      # structure applies to 'while' statements, 'try' blocks, etc). Therefore,
      # we visit all children here and create a new line before the requested
      # set of nodes.
      if (child.type == layout_token.NAME and
          child.value in substatement_names):
        self._StartNewLine()
      self.Visit(child)

  _IF_STMT_ELEMS = frozenset({'if', 'else', 'elif'})

  def Visit_if_stmt(self, node):  # pylint: disable=invalid-name
    self._VisitCompoundStatement(node, self._IF_STMT_ELEMS)

  _WHILE_STMT_ELEMS = frozenset({'while', 'else'})

  def Visit_while_stmt(self, node):  # pylint: disable=invalid-name
    self._VisitCompoundStatement(node, self._WHILE_STMT_ELEMS)

  _FOR_STMT_ELEMS = frozenset({'for', 'else'})

  def Visit_for_stmt(self, node):  # pylint: disable=invalid-name
    self._VisitCompoundStatement(node, self._FOR_STMT_ELEMS)

  _TRY_STMT_ELEMS = frozenset({'try', 'except', 'else', 'finally'})

  def Visit_try_stmt(self, node):  # pylint: disable=invalid-name
    self._VisitCompoundStatement(node, self._TRY_STMT_ELEMS)

  _EXCEPT_STMT_ELEMS = frozenset({'except'})

  def Visit_except_clause(self, node):  # pylint: disable=invalid-name
    self._VisitCompoundStatement(node, self._EXCEPT_STMT_ELEMS)

  _FUNC_DEF_ELEMS = frozenset({'def'})

  def Visit_funcdef(self, node):  # pylint: disable=invalid-name
    self._VisitCompoundStatement(node, self._FUNC_DEF_ELEMS)

  def Visit_async_funcdef(self, node):  # pylint: disable=invalid-name
    self._StartNewLine()
    index = 0
    for child in node.children:
      index += 1
      self.Visit(child)
      if child.type == layout_token.ASYNC:
        break
    for child in node.children[index].children:
      self.Visit(child)

  _CLASS_DEF_ELEMS = frozenset({'class'})

  def Visit_classdef(self, node):  # pylint: disable=invalid-name
    self._VisitCompoundStatement(node, self._CLASS_DEF_ELEMS)

  def Visit_async_stmt(self, node):  # pylint: disable=invalid-name
    self._StartNewLine()
    index = 0
    for child in node.children:
      index += 1
      self.Visit(child)
      if child.type == layout_token.ASYNC:
        break
    for child in node.children[index].children:
      if child.type == layout_token.NAME and child.value == 'else':
        self._StartNewLine()
      self.Visit(child)

  def Visit_decorator(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if child.type == layout_token.COMMENT and child == node.children[0]:
        self._StartNewLine()

  def Visit_decorators(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self._StartNewLine()
      self.Visit(child)

  def Visit_decorated(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self._StartNewLine()
      self.Visit(child)

  _WITH_STMT_ELEMS = frozenset({'with'})

  def Visit_with_stmt(self, node):  # pylint: disable=invalid-name
    self._VisitCompoundStatement(node, self._WITH_STMT_ELEMS)

  _MATCH_STMT_ELEMS = frozenset({'match', 'case'})

  def Visit_match_stmt(self, node):  # pylint: disable=invalid-name
    self._VisitCompoundStatement(node, self._MATCH_STMT_ELEMS)

  _CASE_BLOCK_ELEMS = frozenset({'case'})

  def Visit_case_block(self, node):
    self._cur_depth += 1
    self._StartNewLine()
    self._VisitCompoundStatement(node, self._CASE_BLOCK_ELEMS)
    self._cur_depth -= 1

  def Visit_suite(self, node):  # pylint: disable=invalid-name
    # A 'suite' starts a new indentation level in Python.
    self._cur_depth += 1
    self._StartNewLine()
    self.DefaultNodeVisit(node)
    self._cur_depth -= 1

  def Visit_listmaker(self, node):  # pylint: disable=invalid-name
    _DetermineMustSplitAnnotation(node)
    self.DefaultNodeVisit(node)

  def Visit_dictsetmaker(self, node):  # pylint: disable=invalid-name
    _DetermineMustSplitAnnotation(node)
    self.DefaultNodeVisit(node)

  def Visit_import_as_names(self, node):  # pylint: disable=invalid-name
    if node.prev_sibling.value == '(':
      _DetermineMustSplitAnnotation(node)
    self.DefaultNodeVisit(node)

  def Visit_testlist_gexp(self, node):  # pylint: disable=invalid-name
    _DetermineMustSplitAnnotation(node)
    self.DefaultNodeVisit(node)

  def Visit_arglist(self, node):  # pylint: disable=invalid-name
    _DetermineMustSplitAnnotation(node)
    self.DefaultNodeVisit(node)

  def Visit_typedargslist(self, node):  # pylint: disable=invalid-name
    _DetermineMustSplitAnnotation(node)
    self.DefaultNodeVisit(node)

  def Visit_subscriptlist(self, node):  # pylint: disable=invalid-name
    _DetermineMustSplitAnnotation(node)
    self.DefaultNodeVisit(node)

  def DefaultLeafVisit(self, leaf):
    """Default visitor for tree leaves.

    A tree leaf is always just gets appended to the current logical line.

    Arguments:
      leaf: the leaf to visit.
    """
    if leaf.type in _WHITESPACE_TOKENS:
      self._StartNewLine()
    elif leaf.type != layout_token.COMMENT or leaf.value.strip():
      # Add non-whitespace tokens and comments that aren't empty.
      self._cur_logical_line.AppendToken(
          format_token.FormatToken(leaf, utils.NodeName(leaf)))


_BRACKET_MATCH = {')': '(', '}': '{', ']': '['}


def _MatchBrackets(line):
  """Visit the node and match the brackets.

  For every open bracket ('[', '{', or '('), find the associated closing bracket
  and "match" them up. I.e., save in the token a pointer to its associated open
  or close bracket.

  Arguments:
    line: (LogicalLine) A logical line.
  """
  bracket_stack = []
  for token in line.tokens:
    if token.value in _OPENING_BRACKETS:
      bracket_stack.append(token)
    elif token.value in _CLOSING_BRACKETS:
      bracket_stack[-1].matching_bracket = token
      token.matching_bracket = bracket_stack[-1]
      bracket_stack.pop()

    for bracket in bracket_stack:
      if id(utils.GetOpeningBracket(token.node)) == id(bracket.node):
        bracket.container_elements.append(token)
        token.container_opening = bracket


def _IdentifyParameterLists(line):
  """Visit the node to create a state for parameter lists.

  For instance, a parameter is considered an "object" with its first and last
  token uniquely identifying the object.

  Arguments:
    line: (LogicalLine) A logical line.
  """
  func_stack = []
  param_stack = []
  for tok in line.tokens:
    # Identify parameter list objects.
    if subtypes.FUNC_DEF in tok.subtypes:
      assert tok.next_token.value == '('
      func_stack.append(tok.next_token)
      continue

    if func_stack and tok.value == ')':
      if tok == func_stack[-1].matching_bracket:
        func_stack.pop()
      continue

    # Identify parameter objects.
    if subtypes.PARAMETER_START in tok.subtypes:
      param_stack.append(tok)

    # Not "elif", a parameter could be a single token.
    if param_stack and subtypes.PARAMETER_STOP in tok.subtypes:
      start = param_stack.pop()
      func_stack[-1].parameters.append(object_state.Parameter(start, tok))


def _AdjustSplitPenalty(line):
  """Visit the node and adjust the split penalties if needed.

  A token shouldn't be split if it's not within a bracket pair. Mark any token
  that's not within a bracket pair as "unbreakable".

  Arguments:
    line: (LogicalLine) An logical line.
  """
  bracket_level = 0
  for index, token in enumerate(line.tokens):
    if index and not bracket_level:
      utils.SetNodeAnnotation(token.node, utils.Annotation.SPLIT_PENALTY,
                              split_penalty.UNBREAKABLE)
    if token.value in _OPENING_BRACKETS:
      bracket_level += 1
    elif token.value in _CLOSING_BRACKETS:
      bracket_level -= 1


def _DetermineMustSplitAnnotation(node):
  """Enforce a split in the list if the list ends with a comma."""

  def SplitBecauseTrailingComma():
    if style.Get('DISABLE_ENDING_COMMA_HEURISTIC'):
      return False
    token = next(node.parent.leaves())
    if token.value == '(':
      if sum(1 for ch in node.children if ch.type == layout_token.COMMA) < 2:
        return False
    if (not isinstance(node.children[-1], layout_tree.Leaf) or
        node.children[-1].value != ','):
      return False
    return True

  def SplitBecauseListContainsComment():
    return (not style.Get('DISABLE_SPLIT_LIST_WITH_COMMENT') and
            _ContainsComments(node))

  if (not SplitBecauseTrailingComma() and
      not SplitBecauseListContainsComment()):
    return

  num_children = len(node.children)
  index = 0
  _SetMustSplitOnFirstLeaf(node.children[0])
  while index < num_children - 1:
    child = node.children[index]
    if isinstance(child, layout_tree.Leaf) and child.value == ',':
      next_child = node.children[index + 1]
      if next_child.type == layout_token.COMMENT:
        index += 1
        if index >= num_children - 1:
          break
      _SetMustSplitOnFirstLeaf(node.children[index + 1])
    index += 1


def _ContainsComments(node):
  """Return True if the list has a comment in it."""
  if isinstance(node, layout_tree.Leaf):
    return node.type == layout_token.COMMENT
  for child in node.children:
    if _ContainsComments(child):
      return True
  return False


def _SetMustSplitOnFirstLeaf(node):
  """Set the "must split" annotation on the first leaf node."""
  utils.SetNodeAnnotation(
      utils.FirstLeafNode(node), utils.Annotation.MUST_SPLIT, True)
