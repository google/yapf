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
"""Subtype assigner for format tokens.

This module assigns extra type information to format tokens. This information is
more specific than whether something is an operator or an identifier. For
instance, it can specify if a node in the tree is part of a subscript.

  AssignSubtypes(): the main function exported by this module.

Annotations:
  subtype: The token subtype. See the 'subtypes' module for a list of
      subtypes.
"""

from yapf.layout import tokens as layout_token
from yapf.layout import tree as layout_tree
from yapf.layout import utils
from yapf.layout import visitor
from yapf.layout.roles import Kind as syms
from yapf.yapflib import style
from yapf.yapflib import subtypes


def AssignSubtypes(tree):
  """Run the subtype assigner visitor over the tree, modifying it in place.

  Arguments:
    tree: the top-level layout tree node to annotate with subtypes.
  """
  subtype_assigner = _SubtypeAssigner()
  subtype_assigner.Visit(tree)


# Map tokens in argument lists to their respective subtype.
_ARGLIST_TOKEN_TO_SUBTYPE = {
    '=': subtypes.DEFAULT_OR_NAMED_ASSIGN,
    ':': subtypes.TYPED_NAME,
    '*': subtypes.VARARGS_STAR,
    '**': subtypes.KWARGS_STAR_STAR,
}


class _SubtypeAssigner(visitor.LayoutVisitor):
  """_SubtypeAssigner - see file-level docstring for detailed description.

  The subtype is added as an annotation to the layout tree token.
  """

  def Visit_dictsetmaker(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)

    dict_maker = False

    def markAsDictSetGenerator(node):
      _AppendFirstLeafTokenSubtype(node, subtypes.DICT_SET_GENERATOR)
      for child in node.children:
        if utils.NodeName(child) == 'comp_for':
          markAsDictSetGenerator(child)

    for child in node.children:
      if utils.NodeName(child) == 'comp_for':
        markAsDictSetGenerator(child)
      elif child.type in (layout_token.COLON, layout_token.DOUBLESTAR):
        dict_maker = True

    if dict_maker:
      last_was_colon = False
      unpacking = False
      for child in node.children:
        if utils.NodeName(child) == 'comp_for':
          break
        if child.type == layout_token.DOUBLESTAR:
          _AppendFirstLeafTokenSubtype(child, subtypes.KWARGS_STAR_STAR)
        if last_was_colon:
          if style.Get('INDENT_DICTIONARY_VALUE'):
            _InsertPseudoParentheses(child)
          else:
            _AppendFirstLeafTokenSubtype(child, subtypes.DICTIONARY_VALUE)
        elif (isinstance(child, layout_tree.Node) or
              (not child.value.startswith('#') and child.value not in '{:,')):
          # Mark the first leaf of a key entry as a DICTIONARY_KEY. We
          # normally want to split before them if the dictionary cannot exist
          # on a single line.
          if not unpacking or utils.FirstLeafNode(child).value == '**':
            _AppendFirstLeafTokenSubtype(child, subtypes.DICTIONARY_KEY)
          _AppendSubtypeRec(child, subtypes.DICTIONARY_KEY_PART)
        last_was_colon = child.type == layout_token.COLON
        if child.type == layout_token.DOUBLESTAR:
          unpacking = True
        elif last_was_colon:
          unpacking = False

  def Visit_expr_stmt(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if isinstance(child, layout_tree.Leaf) and child.value == '=':
        _AppendTokenSubtype(child, subtypes.ASSIGN_OPERATOR)

  def Visit_or_test(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if isinstance(child, layout_tree.Leaf) and child.value == 'or':
        _AppendTokenSubtype(child, subtypes.BINARY_OPERATOR)

  def Visit_and_test(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if isinstance(child, layout_tree.Leaf) and child.value == 'and':
        _AppendTokenSubtype(child, subtypes.BINARY_OPERATOR)

  def Visit_not_test(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if isinstance(child, layout_tree.Leaf) and child.value == 'not':
        _AppendTokenSubtype(child, subtypes.UNARY_OPERATOR)

  def Visit_comparison(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if (isinstance(child, layout_tree.Leaf) and
          child.value in {'<', '>', '==', '>=', '<=', '<>', '!=', 'in', 'is'}):
        _AppendTokenSubtype(child, subtypes.BINARY_OPERATOR)
      elif utils.NodeName(child) == 'comp_op':
        for grandchild in child.children:
          _AppendTokenSubtype(grandchild, subtypes.BINARY_OPERATOR)

  def Visit_star_expr(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if isinstance(child, layout_tree.Leaf) and child.value == '*':
        _AppendTokenSubtype(child, subtypes.UNARY_OPERATOR)
        _AppendTokenSubtype(child, subtypes.VARARGS_STAR)

  def Visit_expr(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if isinstance(child, layout_tree.Leaf) and child.value == '|':
        _AppendTokenSubtype(child, subtypes.BINARY_OPERATOR)

  def Visit_xor_expr(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if isinstance(child, layout_tree.Leaf) and child.value == '^':
        _AppendTokenSubtype(child, subtypes.BINARY_OPERATOR)

  def Visit_and_expr(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if isinstance(child, layout_tree.Leaf) and child.value == '&':
        _AppendTokenSubtype(child, subtypes.BINARY_OPERATOR)

  def Visit_shift_expr(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if isinstance(child, layout_tree.Leaf) and child.value in {'<<', '>>'}:
        _AppendTokenSubtype(child, subtypes.BINARY_OPERATOR)

  def Visit_arith_expr(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if _IsAExprOperator(child):
        _AppendTokenSubtype(child, subtypes.BINARY_OPERATOR)

    if _IsSimpleExpression(node):
      for child in node.children:
        if _IsAExprOperator(child):
          _AppendTokenSubtype(child, subtypes.SIMPLE_EXPRESSION)

  def Visit_term(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if _IsMExprOperator(child):
        _AppendTokenSubtype(child, subtypes.BINARY_OPERATOR)

    if _IsSimpleExpression(node):
      for child in node.children:
        if _IsMExprOperator(child):
          _AppendTokenSubtype(child, subtypes.SIMPLE_EXPRESSION)

  def Visit_factor(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if isinstance(child, layout_tree.Leaf) and child.value in '+-~':
        _AppendTokenSubtype(child, subtypes.UNARY_OPERATOR)

  def Visit_power(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if isinstance(child, layout_tree.Leaf) and child.value == '**':
        _AppendTokenSubtype(child, subtypes.BINARY_OPERATOR)

  def Visit_lambdef(self, node):  # pylint: disable=invalid-name
    # trailer: '(' [arglist] ')' | '[' subscriptlist ']' | '.' NAME
    _AppendSubtypeRec(node, subtypes.LAMBDEF)
    self.DefaultNodeVisit(node)

  def Visit_trailer(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if isinstance(child, layout_tree.Leaf) and child.value in '[]':
        _AppendTokenSubtype(child, subtypes.SUBSCRIPT_BRACKET)

  def Visit_subscript(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if isinstance(child, layout_tree.Leaf) and child.value == ':':
        _AppendTokenSubtype(child, subtypes.SUBSCRIPT_COLON)

  def Visit_sliceop(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      self.Visit(child)
      if isinstance(child, layout_tree.Leaf) and child.value == ':':
        _AppendTokenSubtype(child, subtypes.SUBSCRIPT_COLON)

  def Visit_argument(self, node):  # pylint: disable=invalid-name
    #     test [comp_for] | test '=' test
    self._ProcessArgLists(node)

  def Visit_arglist(self, node):  # pylint: disable=invalid-name
    self._ProcessArgLists(node)
    _SetArgListSubtype(node, subtypes.DEFAULT_OR_NAMED_ASSIGN,
                       subtypes.DEFAULT_OR_NAMED_ASSIGN_ARG_LIST)

  def Visit_tname(self, node):  # pylint: disable=invalid-name
    self._ProcessArgLists(node)
    _SetArgListSubtype(node, subtypes.DEFAULT_OR_NAMED_ASSIGN,
                       subtypes.DEFAULT_OR_NAMED_ASSIGN_ARG_LIST)

  def Visit_decorator(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      if isinstance(child, layout_tree.Leaf) and child.value == '@':
        _AppendTokenSubtype(child, subtype=subtypes.DECORATOR)
      self.Visit(child)

  def Visit_funcdef(self, node):  # pylint: disable=invalid-name
    for child in node.children:
      if child.type == layout_token.NAME and child.value != 'def':
        _AppendTokenSubtype(child, subtypes.FUNC_DEF)
        break
    for child in node.children:
      self.Visit(child)

  def Visit_parameters(self, node):  # pylint: disable=invalid-name
    self._ProcessArgLists(node)
    if len(node.children) > 2:
      _AppendFirstLeafTokenSubtype(node.children[1], subtypes.PARAMETER_START)
      _AppendLastLeafTokenSubtype(node.children[-2], subtypes.PARAMETER_STOP)

  def Visit_typedargslist(self, node):  # pylint: disable=invalid-name
    self._ProcessArgLists(node)
    _SetArgListSubtype(node, subtypes.DEFAULT_OR_NAMED_ASSIGN,
                       subtypes.DEFAULT_OR_NAMED_ASSIGN_ARG_LIST)
    tname = False
    if not node.children:
      return

    _AppendFirstLeafTokenSubtype(node.children[0], subtypes.PARAMETER_START)
    _AppendLastLeafTokenSubtype(node.children[-1], subtypes.PARAMETER_STOP)

    tname = utils.NodeName(node.children[0]) == 'tname'
    for i in range(1, len(node.children)):
      prev_child = node.children[i - 1]
      child = node.children[i]
      if prev_child.type == layout_token.COMMA:
        _AppendFirstLeafTokenSubtype(child, subtypes.PARAMETER_START)
      elif child.type == layout_token.COMMA:
        _AppendLastLeafTokenSubtype(prev_child, subtypes.PARAMETER_STOP)

      if utils.NodeName(child) == 'tname':
        tname = True
        _SetArgListSubtype(child, subtypes.TYPED_NAME,
                           subtypes.TYPED_NAME_ARG_LIST)
      elif child.type == layout_token.COMMA:
        tname = False
      elif child.type == layout_token.EQUAL and tname:
        _AppendTokenSubtype(child, subtype=subtypes.TYPED_NAME)
        tname = False

  def Visit_varargslist(self, node):  # pylint: disable=invalid-name
    self._ProcessArgLists(node)
    for child in node.children:
      self.Visit(child)
      if isinstance(child, layout_tree.Leaf) and child.value == '=':
        _AppendTokenSubtype(child, subtypes.VARARGS_LIST)

  def Visit_comp_for(self, node):  # pylint: disable=invalid-name
    _AppendSubtypeRec(node, subtypes.COMP_FOR)
    # Mark the previous node as COMP_EXPR unless this is a nested comprehension
    # as these will have the outer comprehension as their previous node.
    attr = utils.GetNodeAnnotation(node.parent, utils.Annotation.SUBTYPE)
    if not attr or subtypes.COMP_FOR not in attr:
      sibling = node.prev_sibling
      while sibling:
        _AppendSubtypeRec(sibling, subtypes.COMP_EXPR)
        sibling = sibling.prev_sibling
    self.DefaultNodeVisit(node)

  def Visit_comp_if(self, node):  # pylint: disable=invalid-name
    _AppendSubtypeRec(node, subtypes.COMP_IF)
    self.DefaultNodeVisit(node)

  def _ProcessArgLists(self, node):
    """Common method for processing argument lists."""
    for child in node.children:
      self.Visit(child)
      if isinstance(child, layout_tree.Leaf):
        _AppendTokenSubtype(
            child,
            subtype=_ARGLIST_TOKEN_TO_SUBTYPE.get(child.value, subtypes.NONE))


def _SetArgListSubtype(node, node_subtype, list_subtype):
  """Set named assign subtype on elements in a arg list."""

  def HasSubtype(node):
    """Return True if the arg list has a named assign subtype."""
    if isinstance(node, layout_tree.Leaf):
      return node_subtype in utils.GetNodeAnnotation(node,
                                                     utils.Annotation.SUBTYPE,
                                                     set())

    for child in node.children:
      node_name = utils.NodeName(child)
      if node_name not in {'atom', 'arglist', 'power'}:
        if HasSubtype(child):
          return True

    return False

  if not HasSubtype(node):
    return

  for child in node.children:
    node_name = utils.NodeName(child)
    if node_name not in {'atom', 'COMMA'}:
      _AppendFirstLeafTokenSubtype(child, list_subtype)


def _AppendTokenSubtype(node, subtype):
  """Append the token's subtype only if it's not already set."""
  utils.AppendNodeAnnotation(node, utils.Annotation.SUBTYPE, subtype)


def _AppendFirstLeafTokenSubtype(node, subtype):
  """Append the first leaf token's subtypes."""
  if isinstance(node, layout_tree.Leaf):
    _AppendTokenSubtype(node, subtype)
    return
  _AppendFirstLeafTokenSubtype(node.children[0], subtype)


def _AppendLastLeafTokenSubtype(node, subtype):
  """Append the last leaf token's subtypes."""
  if isinstance(node, layout_tree.Leaf):
    _AppendTokenSubtype(node, subtype)
    return
  _AppendLastLeafTokenSubtype(node.children[-1], subtype)


def _AppendSubtypeRec(node, subtype, force=True):
  """Append the leafs in the node to the given subtype."""
  if isinstance(node, layout_tree.Leaf):
    _AppendTokenSubtype(node, subtype)
    return
  for child in node.children:
    _AppendSubtypeRec(child, subtype, force=force)


def _InsertPseudoParentheses(node):
  """Insert pseudo parentheses so that dicts can be formatted correctly."""
  comment_node = None
  if isinstance(node, layout_tree.Node):
    if node.children[-1].type == layout_token.COMMENT:
      comment_node = node.children[-1].clone()
      node.children[-1].remove()

  first = utils.FirstLeafNode(node)
  last = utils.LastLeafNode(node)

  if first == last and first.type == layout_token.COMMENT:
    # A comment was inserted before the value, which is a layout_tree.Leaf.
    # Encompass the dictionary's value into an ATOM node.
    last = first.next_sibling
    last_clone = last.clone()
    new_node = layout_tree.Node(syms.atom, [first.clone(), last_clone])
    for orig_leaf, clone_leaf in zip(last.leaves(), last_clone.leaves()):
      utils.CopyYapfAnnotations(orig_leaf, clone_leaf)
      if hasattr(orig_leaf, 'is_pseudo'):
        clone_leaf.is_pseudo = orig_leaf.is_pseudo

    node.replace(new_node)
    node = new_node
    last.remove()

    first = utils.FirstLeafNode(node)
    last = utils.LastLeafNode(node)

  lparen = layout_tree.Leaf(
      layout_token.LPAR,
      '(',
      context=('', (first.get_lineno(), first.column - 1)))
  last_lineno = last.get_lineno()
  if last.type == layout_token.STRING and '\n' in last.value:
    last_lineno += last.value.count('\n')

  if last.type == layout_token.STRING and '\n' in last.value:
    last_column = len(last.value.split('\n')[-1]) + 1
  else:
    last_column = last.column + len(last.value) + 1
  rparen = layout_tree.Leaf(
      layout_token.RPAR, ')', context=('', (last_lineno, last_column)))

  lparen.is_pseudo = True
  rparen.is_pseudo = True

  if isinstance(node, layout_tree.Node):
    node.insert_child(0, lparen)
    node.append_child(rparen)
    if comment_node:
      node.append_child(comment_node)
    _AppendFirstLeafTokenSubtype(node, subtypes.DICTIONARY_VALUE)
  else:
    clone = node.clone()
    for orig_leaf, clone_leaf in zip(node.leaves(), clone.leaves()):
      utils.CopyYapfAnnotations(orig_leaf, clone_leaf)
    new_node = layout_tree.Node(syms.atom, [lparen, clone, rparen])
    node.replace(new_node)
    _AppendFirstLeafTokenSubtype(clone, subtypes.DICTIONARY_VALUE)


def _IsAExprOperator(node):
  return isinstance(node, layout_tree.Leaf) and node.value in {'+', '-'}


def _IsMExprOperator(node):
  return isinstance(
      node, layout_tree.Leaf) and node.value in {'*', '/', '%', '//', '@'}


def _IsSimpleExpression(node):
  """A node with only leafs as children."""
  return all(isinstance(child, layout_tree.Leaf) for child in node.children)
