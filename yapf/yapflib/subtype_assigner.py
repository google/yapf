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
"""Subtype assigner for lib2to3 trees.

This module assigns extra type information to the lib2to3 trees. This
information is more specific than whether something is an operator or an
identifier. For instance, it can specify if a node in the tree is part of a
subscript.

  AssignSubtypes(): the main function exported by this module.

Annotations:
  subtype: The subtype of a pytree token. See 'format_token' module for a list
      of subtypes.
"""

from lib2to3 import pytree

from yapf.yapflib import format_token
from yapf.yapflib import pytree_utils
from yapf.yapflib import pytree_visitor


def AssignSubtypes(tree):
  """Run the subtype assigner visitor over the tree, modifying it in place.

  Arguments:
    tree: the top-level pytree node to annotate with subtypes.
  """
  subtype_assigner = _SubtypeAssigner()
  subtype_assigner.Visit(tree)

# Map tokens in argument lists to their respective subtype.
_ARGLIST_TOKEN_TO_SUBTYPE = {
    '=': format_token.Subtype.DEFAULT_OR_NAMED_ASSIGN,
    '*': format_token.Subtype.VARARGS_STAR,
    '**': format_token.Subtype.KWARGS_STAR_STAR,
}


class _SubtypeAssigner(pytree_visitor.PyTreeVisitor):
  """_SubtypeAssigner - see file-level docstring for detailed description.

  The subtype is added as an annotation to the pytree token.
  """

  def Visit_dictsetmaker(self, node):  # pylint: disable=invalid-name
    # dictsetmaker ::= (test ':' test (comp_for |
    #                                   (',' test ':' test)* [','])) |
    #                  (test (comp_for | (',' test)* [',']))
    dict_maker = (len(node.children) > 1 and isinstance(
        node.children[1], pytree.Leaf) and node.children[1].value == ':')
    last_was_comma = False
    last_was_colon = False
    for child in node.children:
      if pytree_utils.NodeName(child) == 'comp_for':
        self._SetFirstLeafTokenSubtype(child,
                                       format_token.Subtype.DICT_SET_GENERATOR)
      else:
        if dict_maker:
          if last_was_comma:
            self._SetFirstLeafTokenSubtype(child,
                                           format_token.Subtype.DICTIONARY_KEY)
          elif last_was_colon:
            if pytree_utils.NodeName(child) == 'power':
              self._SetSubtypeRec(child, format_token.Subtype.NONE, force=True)
            else:
              self._SetSubtypeRec(child, format_token.Subtype.DICTIONARY_VALUE)
        last_was_comma = isinstance(child, pytree.Leaf) and child.value == ','
        last_was_colon = isinstance(child, pytree.Leaf) and child.value == ':'
      self.Visit(child)

  def Visit_expr_stmt(self, node):  # pylint: disable=invalid-name
    # expr_stmt ::= testlist_star_expr (augassign (yield_expr|testlist)
    #               | ('=' (yield_expr|testlist_star_expr))*)
    for child in node.children:
      self.Visit(child)
      if isinstance(child, pytree.Leaf) and child.value == '=':
        self._SetTokenSubtype(child, format_token.Subtype.ASSIGN_OPERATOR, True)

  def Visit_if_stmt(self, node):  # pylint: disable=invalid-name
    # if_stmt ::= 'if' test ':' suite ('elif' test ':' suite)*
    #             ['else' ':' suite]
    for child in node.children:
      self.Visit(child)
      if pytree_utils.NodeName(child).endswith('test'):
        self._SetTokenExprTypeRec(child, format_token.ExprType.IF_TEST_EXPR)

  def Visit_or_test(self, node):  # pylint: disable=invalid-name
    # or_test ::= and_test ('or' and_test)*
    for child in node.children:
      self.Visit(child)
      if isinstance(child, pytree.Leaf) and child.value == 'or':
        self._SetTokenSubtype(child, format_token.Subtype.BINARY_OPERATOR, True)

  def Visit_and_test(self, node):  # pylint: disable=invalid-name
    # and_test ::= not_test ('and' not_test)*
    for child in node.children:
      self.Visit(child)
      if isinstance(child, pytree.Leaf) and child.value == 'and':
        self._SetTokenSubtype(child, format_token.Subtype.BINARY_OPERATOR, True)

  def Visit_not_test(self, node):  # pylint: disable=invalid-name
    # not_test ::= 'not' not_test | comparison
    for child in node.children:
      self.Visit(child)
      if isinstance(child, pytree.Leaf) and child.value == 'not':
        self._SetTokenSubtype(child, format_token.Subtype.UNARY_OPERATOR, True)

  def Visit_comparison(self, node):  # pylint: disable=invalid-name
    # comparison ::= expr (comp_op expr)*
    # comp_op ::= '<'|'>'|'=='|'>='|'<='|'<>'|'!='|'in'|'not in'|'is'|'is not'
    for child in node.children:
      self.Visit(child)
      if (isinstance(child, pytree.Leaf) and child.value in {
          '<', '>', '==', '>=', '<=', '<>', '!=', 'in', 'not in', 'is', 'is not'
      }):
        self._SetTokenSubtype(child, format_token.Subtype.BINARY_OPERATOR, True)

  def Visit_star_expr(self, node):  # pylint: disable=invalid-name
    # star_expr ::= '*' expr
    for child in node.children:
      self.Visit(child)
      if isinstance(child, pytree.Leaf) and child.value == '*':
        self._SetTokenSubtype(child, format_token.Subtype.UNARY_OPERATOR, True)

  def Visit_expr(self, node):  # pylint: disable=invalid-name
    # expr ::= xor_expr ('|' xor_expr)*
    for child in node.children:
      self.Visit(child)
      if isinstance(child, pytree.Leaf) and child.value == '|':
        self._SetTokenSubtype(child, format_token.Subtype.BINARY_OPERATOR, True)

  def Visit_xor_expr(self, node):  # pylint: disable=invalid-name
    # xor_expr ::= and_expr ('^' and_expr)*
    for child in node.children:
      self.Visit(child)
      if isinstance(child, pytree.Leaf) and child.value == '^':
        self._SetTokenSubtype(child, format_token.Subtype.BINARY_OPERATOR, True)

  def Visit_and_expr(self, node):  # pylint: disable=invalid-name
    # and_expr ::= shift_expr ('&' shift_expr)*
    for child in node.children:
      self.Visit(child)
      if isinstance(child, pytree.Leaf) and child.value == '&':
        self._SetTokenSubtype(child, format_token.Subtype.BINARY_OPERATOR, True)

  def Visit_shift_expr(self, node):  # pylint: disable=invalid-name
    # shift_expr ::= arith_expr (('<<'|'>>') arith_expr)*
    for child in node.children:
      self.Visit(child)
      if isinstance(child, pytree.Leaf) and child.value in {'<<', '>>'}:
        self._SetTokenSubtype(child, format_token.Subtype.BINARY_OPERATOR, True)

  def Visit_arith_expr(self, node):  # pylint: disable=invalid-name
    # arith_expr ::= term (('+'|'-') term)*
    for child in node.children:
      self.Visit(child)
      if isinstance(child, pytree.Leaf) and child.value in '+-':
        self._SetTokenSubtype(child, format_token.Subtype.BINARY_OPERATOR, True)

  def Visit_term(self, node):  # pylint: disable=invalid-name
    # term ::= factor (('*'|'/'|'%'|'//') factor)*
    for child in node.children:
      self.Visit(child)
      if (isinstance(child, pytree.Leaf) and
          child.value in {'*', '/', '%', '//'}):
        self._SetTokenSubtype(child, format_token.Subtype.BINARY_OPERATOR, True)

  def Visit_factor(self, node):  # pylint: disable=invalid-name
    # factor ::= ('+'|'-'|'~') factor | power
    for child in node.children:
      self.Visit(child)
      if isinstance(child, pytree.Leaf) and child.value in '+-~':
        self._SetTokenSubtype(child, format_token.Subtype.UNARY_OPERATOR, True)

  def Visit_power(self, node):  # pylint: disable=invalid-name
    # power ::= atom trailer* ['**' factor]
    for child in node.children:
      self.Visit(child)
      if isinstance(child, pytree.Leaf) and child.value == '**':
        self._SetTokenSubtype(child, format_token.Subtype.BINARY_OPERATOR, True)

  def Visit_subscript(self, node):  # pylint: disable=invalid-name
    # subscript ::= test | [test] ':' [test] [sliceop]
    for child in node.children:
      self.Visit(child)
      if isinstance(child, pytree.Leaf) and child.value == ':':
        self._SetTokenSubtype(child, format_token.Subtype.SUBSCRIPT_COLON, True)

  def Visit_sliceop(self, node):  # pylint: disable=invalid-name
    # sliceop ::= ':' [test]
    for child in node.children:
      self.Visit(child)
      if isinstance(child, pytree.Leaf) and child.value == ':':
        self._SetTokenSubtype(child, format_token.Subtype.SUBSCRIPT_COLON, True)

  def Visit_argument(self, node):  # pylint: disable=invalid-name
    # argument ::=
    #     test [comp_for] | test '=' test
    self._ProcessArgLists(node)

  def Visit_arglist(self, node):  # pylint: disable=invalid-name
    # arglist ::=
    #     (argument ',')* (argument [',']
    #                     | '*' test (',' argument)* [',' '**' test]
    #                     | '**' test)
    self._ProcessArgLists(node)

  def Visit_typedargslist(self, node):  # pylint: disable=invalid-name
    # typedargslist ::=
    #     ((tfpdef ['=' test] ',')*
    #          ('*' [tname] (',' tname ['=' test])* [',' '**' tname]
    #           | '**' tname)
    #     | tfpdef ['=' test] (',' tfpdef ['=' test])* [','])
    self._ProcessArgLists(node)

  def Visit_varargslist(self, node):  # pylint: disable=invalid-name
    # varargslist ::=
    #     ((vfpdef ['=' test] ',')*
    #          ('*' [vname] (',' vname ['=' test])*  [',' '**' vname]
    #           | '**' vname)
    #      | vfpdef ['=' test] (',' vfpdef ['=' test])* [','])
    self._ProcessArgLists(node)

  def Visit_comp_for(self, node):  # pylint: disable=invalid-name
    # comp_for ::= 'for' exprlist 'in' testlist_safe [comp_iter]
    self._SetFirstLeafTokenSubtype(node, format_token.Subtype.COMP_FOR)
    self.DefaultNodeVisit(node)

  def Visit_comp_if(self, node):  # pylint: disable=invalid-name
    # comp_if ::= 'if' old_test [comp_iter]
    self._SetFirstLeafTokenSubtype(node, format_token.Subtype.COMP_IF)
    self.DefaultNodeVisit(node)

  def _ProcessArgLists(self, node):
    """Common method for processing argument lists."""
    self._SetTokenExprTypeRec(node, format_token.ExprType.DONT_TOUCH)
    for child in node.children:
      self.Visit(child)
      if isinstance(child, pytree.Leaf):
        self._SetTokenSubtype(child,
                              subtype=_ARGLIST_TOKEN_TO_SUBTYPE.get(
                                  child.value, format_token.Subtype.NONE))

  def _SetSubtypeRec(self, node, subtype, force=False):
    """Set the leafs in the node to the given subtype."""
    if isinstance(node, pytree.Leaf):
      self._SetTokenSubtype(node, subtype, force=force)
      return
    for child in node.children:
      self._SetSubtypeRec(child, subtype, force=force)

  def _SetTokenSubtype(self, node, subtype, force=False):
    """Set the token's subtype only if it's not already set."""
    if force or not pytree_utils.GetNodeAnnotation(
        node, pytree_utils.Annotation.SUBTYPE):
      pytree_utils.SetNodeAnnotation(node, pytree_utils.Annotation.SUBTYPE,
                                     subtype)

  def _SetFirstLeafTokenSubtype(self, node, subtype, force=False):
    """Set the first leaf token's subtypes."""
    if isinstance(node, pytree.Leaf):
      self._SetTokenSubtype(node, subtype, force=force)
      return
    self._SetFirstLeafTokenSubtype(node.children[0], subtype, force=force)

  def _SetTokenExprTypeRec(self, node, expr_type):
    """Set the leafs in the node to the given expression type."""
    if isinstance(node, pytree.Leaf):
      self._SetTokenExprType(node, expr_type)
      return
    for child in node.children:
      self._SetTokenExprTypeRec(child, expr_type)

  def _SetTokenExprType(self, node, expr_type):
    """Set the token's expr_type only if it's not already set."""
    if not pytree_utils.GetNodeAnnotation(node,
                                          pytree_utils.Annotation.EXPR_TYPE):
      pytree_utils.SetNodeAnnotation(node, pytree_utils.Annotation.EXPR_TYPE,
                                     expr_type)
