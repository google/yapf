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
"""Calculate the number of blank lines between top-level entities.

Calculates how many blank lines we need between classes, functions, and other
entities at the same level.

  CalculateBlankLines(): the main function exported by this module.

Annotations:
  newlines: The number of newlines required before the node.
"""

from yapf_third_party._ylib2to3.pgen2 import token as grammar_token

from yapf.pytree import pytree_utils
from yapf.pytree import pytree_visitor
from yapf.yapflib import style

_NO_BLANK_LINES = 1
_ONE_BLANK_LINE = 2
_TWO_BLANK_LINES = 3

_PYTHON_STATEMENTS = frozenset({
    'small_stmt', 'expr_stmt', 'print_stmt', 'del_stmt', 'pass_stmt',
    'break_stmt', 'continue_stmt', 'return_stmt', 'raise_stmt', 'yield_stmt',
    'import_stmt', 'global_stmt', 'exec_stmt', 'assert_stmt', 'if_stmt',
    'while_stmt', 'for_stmt', 'try_stmt', 'with_stmt', 'nonlocal_stmt',
    'async_stmt', 'simple_stmt'
})


def CalculateBlankLines(tree):
  """Run the blank line calculator visitor over the tree.

  This modifies the tree in place.

  Arguments:
    tree: the top-level pytree node to annotate with subtypes.
  """
  blank_line_calculator = _BlankLineCalculator()
  blank_line_calculator.Visit(tree)


class _BlankLineCalculator(pytree_visitor.PyTreeVisitor):
  """_BlankLineCalculator - see file-level docstring for a description."""

  def __init__(self):
    self.class_level = 0
    self.function_level = 0
    self.last_comment_lineno = 0
    self.last_was_decorator = False
    self.last_was_class_or_function = False

  def Visit_simple_stmt(self, node):  # pylint: disable=invalid-name
    self.DefaultNodeVisit(node)
    if node.children[0].type == grammar_token.COMMENT:
      self.last_comment_lineno = node.children[0].lineno

  def Visit_decorator(self, node):  # pylint: disable=invalid-name
    if (self.last_comment_lineno and
        self.last_comment_lineno == node.children[0].lineno - 1):
      _SetNumNewlines(node.children[0], _NO_BLANK_LINES)
    else:
      _SetNumNewlines(node.children[0], self._GetNumNewlines(node))
    for child in node.children:
      self.Visit(child)
    self.last_was_decorator = True

  def Visit_classdef(self, node):  # pylint: disable=invalid-name
    self.last_was_class_or_function = False
    index = self._SetBlankLinesBetweenCommentAndClassFunc(node)
    self.last_was_decorator = False
    self.class_level += 1
    for child in node.children[index:]:
      self.Visit(child)
    self.class_level -= 1
    self.last_was_class_or_function = True

  def Visit_funcdef(self, node):  # pylint: disable=invalid-name
    self.last_was_class_or_function = False
    index = self._SetBlankLinesBetweenCommentAndClassFunc(node)
    if _AsyncFunction(node):
      index = self._SetBlankLinesBetweenCommentAndClassFunc(
          node.prev_sibling.parent)
      _SetNumNewlines(node.children[0], None)
    else:
      index = self._SetBlankLinesBetweenCommentAndClassFunc(node)
    self.last_was_decorator = False
    self.function_level += 1
    for child in node.children[index:]:
      self.Visit(child)
    self.function_level -= 1
    self.last_was_class_or_function = True

  def DefaultNodeVisit(self, node):
    """Override the default visitor for Node.

    This will set the blank lines required if the last entity was a class or
    function.

    Arguments:
      node: (pytree.Node) The node to visit.
    """
    if self.last_was_class_or_function:
      if pytree_utils.NodeName(node) in _PYTHON_STATEMENTS:
        leaf = pytree_utils.FirstLeafNode(node)
        _SetNumNewlines(leaf, self._GetNumNewlines(leaf))
    self.last_was_class_or_function = False
    super(_BlankLineCalculator, self).DefaultNodeVisit(node)

  def _SetBlankLinesBetweenCommentAndClassFunc(self, node):
    """Set the number of blanks between a comment and class or func definition.

    Class and function definitions have leading comments as children of the
    classdef and functdef nodes.

    Arguments:
      node: (pytree.Node) The classdef or funcdef node.

    Returns:
      The index of the first child past the comment nodes.
    """
    index = 0
    while pytree_utils.IsCommentStatement(node.children[index]):
      # Standalone comments are wrapped in a simple_stmt node with the comment
      # node as its only child.
      self.Visit(node.children[index].children[0])
      if not self.last_was_decorator:
        _SetNumNewlines(node.children[index].children[0], _ONE_BLANK_LINE)
      index += 1
    if (index and node.children[index].lineno - 1
        == node.children[index - 1].children[0].lineno):
      _SetNumNewlines(node.children[index], _NO_BLANK_LINES)
    else:
      if self.last_comment_lineno + 1 == node.children[index].lineno:
        num_newlines = _NO_BLANK_LINES
      else:
        num_newlines = self._GetNumNewlines(node)
      _SetNumNewlines(node.children[index], num_newlines)
    return index

  def _GetNumNewlines(self, node):
    if self.last_was_decorator:
      return _NO_BLANK_LINES
    elif self._IsTopLevel(node):
      return 1 + style.Get('BLANK_LINES_AROUND_TOP_LEVEL_DEFINITION')
    return _ONE_BLANK_LINE

  def _IsTopLevel(self, node):
    return (not (self.class_level or self.function_level) and
            _StartsInZerothColumn(node))


def _SetNumNewlines(node, num_newlines):
  pytree_utils.SetNodeAnnotation(node, pytree_utils.Annotation.NEWLINES,
                                 num_newlines)


def _StartsInZerothColumn(node):
  return (pytree_utils.FirstLeafNode(node).column == 0 or
          (_AsyncFunction(node) and node.prev_sibling.column == 0))


def _AsyncFunction(node):
  return (node.prev_sibling and node.prev_sibling.type == grammar_token.ASYNC)
