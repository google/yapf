# Copyright 2022 Bill Wendling, All Rights Reserved.
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

import ast

from yapf.pyparser import pyparser_utils as pyutils
from yapf.yapflib import split_penalty
from yapf.yapflib import style
from yapf.yapflib import subtypes


class SplitPenalty(ast.NodeVisitor):
  """Compute split penalties between tokens."""

  def __init__(self, logical_lines):
    super(SplitPenalty, self).__init__()
    self.logical_lines = logical_lines

    # We never want to split before a colon or comma.
    for logical_line in logical_lines:
      for token in logical_line.tokens:
        if token.value in frozenset({',', ':'}):
          token.split_penalty = split_penalty.UNBREAKABLE

  def _GetTokens(self, node):
    return pyutils.GetLogicalLine(self.logical_lines, node)

  ############################################################################
  # Statements                                                               #
  ############################################################################

  def visit_FunctionDef(self, node):
    # FunctionDef(name=Name,
    #             args=arguments(
    #                 posonlyargs=[],
    #                 args=[],
    #                 vararg=[],
    #                 kwonlyargs=[],
    #                 kw_defaults=[],
    #                 defaults=[]),
    #             body=[...],
    #             decorator_list=[Call_1, Call_2, ..., Call_n],
    #             keywords=[])
    tokens = self._GetTokens(node)

    for decorator in node.decorator_list:
      # The decorator token list begins after the '@'. The body of the decorator
      # is formatted like a normal "call."
      decorator_range = self._GetTokens(decorator)
      # Don't split after the '@'.
      decorator_range[0].split_penalty = split_penalty.UNBREAKABLE

    for token in tokens[1:]:
      if token.value == '(':
        break
      _SetPenalty(token, split_penalty.UNBREAKABLE)

    if node.returns:
      start_index = pyutils.GetTokenIndex(tokens,
                                          pyutils.TokenStart(node.returns))
      _IncreasePenalty(tokens[start_index - 1:start_index + 1],
                       split_penalty.VERY_STRONGLY_CONNECTED)
      end_index = pyutils.GetTokenIndex(tokens, pyutils.TokenEnd(node.returns))
      _IncreasePenalty(tokens[start_index + 1:end_index],
                       split_penalty.STRONGLY_CONNECTED)

    return self.generic_visit(node)

  def visit_AsyncFunctionDef(self, node):
    # AsyncFunctionDef(name=Name,
    #                  args=arguments(
    #                      posonlyargs=[],
    #                      args=[],
    #                      vararg=[],
    #                      kwonlyargs=[],
    #                      kw_defaults=[],
    #                      defaults=[]),
    #                  body=[...],
    #                  decorator_list=[Expr_1, Expr_2, ..., Expr_n],
    #                  keywords=[])
    return self.visit_FunctionDef(node)

  def visit_ClassDef(self, node):
    # ClassDef(name=Name,
    #          bases=[Expr_1, Expr_2, ..., Expr_n],
    #          keywords=[],
    #          body=[],
    #          decorator_list=[Expr_1, Expr_2, ..., Expr_m])
    for base in node.bases:
      tokens = self._GetTokens(base)
      _IncreasePenalty(tokens[1:], split_penalty.EXPR)

    for decorator in node.decorator_list:
      # Don't split after the '@'.
      tokens = self._GetTokens(decorator)
      tokens[0].split_penalty = split_penalty.UNBREAKABLE

    return self.generic_visit(node)

  def visit_Return(self, node):
    # Return(value=Expr)
    tokens = self._GetTokens(node)
    _IncreasePenalty(tokens[1:], split_penalty.EXPR)

    return self.generic_visit(node)

  def visit_Delete(self, node):
    # Delete(targets=[Expr_1, Expr_2, ..., Expr_n])
    for target in node.targets:
      tokens = self._GetTokens(target)
      _IncreasePenalty(tokens[1:], split_penalty.EXPR)

    return self.generic_visit(node)

  def visit_Assign(self, node):
    # Assign(targets=[Expr_1, Expr_2, ..., Expr_n],
    #        value=Expr)
    tokens = self._GetTokens(node)
    _IncreasePenalty(tokens[1:], split_penalty.EXPR)

    return self.generic_visit(node)

  def visit_AugAssign(self, node):
    # AugAssign(target=Name,
    #           op=Add(),
    #           value=Expr)
    return self.generic_visit(node)

  def visit_AnnAssign(self, node):
    # AnnAssign(target=Expr,
    #           annotation=TypeName,
    #           value=Expr,
    #           simple=number)
    return self.generic_visit(node)

  def visit_For(self, node):
    # For(target=Expr,
    #     iter=Expr,
    #     body=[...],
    #     orelse=[...])
    return self.generic_visit(node)

  def visit_AsyncFor(self, node):
    # AsyncFor(target=Expr,
    #          iter=Expr,
    #          body=[...],
    #          orelse=[...])
    return self.generic_visit(node)

  def visit_While(self, node):
    # While(test=Expr,
    #       body=[...],
    #       orelse=[...])
    return self.generic_visit(node)

  def visit_If(self, node):
    # If(test=Expr,
    #    body=[...],
    #    orelse=[...])
    return self.generic_visit(node)

  def visit_With(self, node):
    # With(items=[withitem_1, withitem_2, ..., withitem_n],
    #      body=[...])
    return self.generic_visit(node)

  def visit_AsyncWith(self, node):
    # AsyncWith(items=[withitem_1, withitem_2, ..., withitem_n],
    #           body=[...])
    return self.generic_visit(node)

  def visit_Match(self, node):
    # Match(subject=Expr,
    #       cases=[
    #           match_case(
    #               pattern=pattern,
    #               guard=Expr,
    #               body=[...]),
    #             ...
    #       ])
    return self.generic_visit(node)

  def visit_Raise(self, node):
    # Raise(exc=Expr)
    return self.generic_visit(node)

  def visit_Try(self, node):
    # Try(body=[...],
    #     handlers=[ExceptHandler_1, ExceptHandler_2, ..., ExceptHandler_b],
    #     orelse=[...],
    #     finalbody=[...])
    return self.generic_visit(node)

  def visit_Assert(self, node):
    # Assert(test=Expr)
    return self.generic_visit(node)

  def visit_Import(self, node):
    # Import(names=[
    #            alias(
    #                name=Identifier,
    #                asname=Identifier),
    #              ...
    #        ])
    return self.generic_visit(node)

  def visit_ImportFrom(self, node):
    # ImportFrom(module=Identifier,
    #            names=[
    #                alias(
    #                    name=Identifier,
    #                    asname=Identifier),
    #                  ...
    #            ],
    #            level=num
    return self.generic_visit(node)

  def visit_Global(self, node):
    # Global(names=[Identifier_1, Identifier_2, ..., Identifier_n])
    return self.generic_visit(node)

  def visit_Nonlocal(self, node):
    # Nonlocal(names=[Identifier_1, Identifier_2, ..., Identifier_n])
    return self.generic_visit(node)

  def visit_Expr(self, node):
    # Expr(value=Expr)
    return self.generic_visit(node)

  def visit_Pass(self, node):
    # Pass()
    return self.generic_visit(node)

  def visit_Break(self, node):
    # Break()
    return self.generic_visit(node)

  def visit_Continue(self, node):
    # Continue()
    return self.generic_visit(node)

  ############################################################################
  # Expressions                                                              #
  ############################################################################

  def visit_BoolOp(self, node):
    # BoolOp(op=And | Or,
    #        values=[Expr_1, Expr_2, ..., Expr_n])
    tokens = self._GetTokens(node)
    _IncreasePenalty(tokens[1:], split_penalty.EXPR)

    # Lower the split penalty to allow splitting before or after the logical
    # operator.
    split_before_operator = style.Get('SPLIT_BEFORE_LOGICAL_OPERATOR')
    operator_indices = [
        pyutils.GetNextTokenIndex(tokens, pyutils.TokenEnd(value))
        for value in node.values[:-1]
    ]
    for operator_index in operator_indices:
      if not split_before_operator:
        operator_index += 1
      _DecreasePenalty(tokens[operator_index], split_penalty.EXPR * 2)

    return self.generic_visit(node)

  def visit_NamedExpr(self, node):
    # NamedExpr(target=Name,
    #           value=Expr)
    tokens = self._GetTokens(node)
    _IncreasePenalty(tokens[1:], split_penalty.EXPR)

    return self.generic_visit(node)

  def visit_BinOp(self, node):
    # BinOp(left=LExpr
    #       op=Add | Sub | Mult | MatMult | Div | Mod | Pow | LShift |
    #          RShift | BitOr | BitXor | BitAnd | FloorDiv
    #       right=RExpr)
    tokens = self._GetTokens(node)

    _IncreasePenalty(tokens[1:], split_penalty.EXPR)

    # Lower the split penalty to allow splitting before or after the arithmetic
    # operator.
    operator_index = pyutils.GetNextTokenIndex(tokens,
                                               pyutils.TokenEnd(node.left))
    if not style.Get('SPLIT_BEFORE_ARITHMETIC_OPERATOR'):
      operator_index += 1

    _DecreasePenalty(tokens[operator_index], split_penalty.EXPR * 2)

    return self.generic_visit(node)

  def visit_UnaryOp(self, node):
    # UnaryOp(op=Not | USub | UAdd | Invert,
    #         operand=Expr)
    tokens = self._GetTokens(node)
    _IncreasePenalty(tokens[1:], split_penalty.EXPR)
    _IncreasePenalty(tokens[1], style.Get('SPLIT_PENALTY_AFTER_UNARY_OPERATOR'))

    return self.generic_visit(node)

  def visit_Lambda(self, node):
    # Lambda(args=arguments(
    #            posonlyargs=[arg(...), arg(...), ..., arg(...)],
    #            args=[arg(...), arg(...), ..., arg(...)],
    #            kwonlyargs=[arg(...), arg(...), ..., arg(...)],
    #            kw_defaults=[arg(...), arg(...), ..., arg(...)],
    #            defaults=[arg(...), arg(...), ..., arg(...)]),
    #        body=Expr)
    tokens = self._GetTokens(node)
    _IncreasePenalty(tokens[1:], split_penalty.LAMBDA)

    if style.Get('ALLOW_MULTILINE_LAMBDAS'):
      _SetPenalty(self._GetTokens(node.body), split_penalty.MULTIPLINE_LAMBDA)

    return self.generic_visit(node)

  def visit_IfExp(self, node):
    # IfExp(test=TestExpr,
    #       body=BodyExpr,
    #       orelse=OrElseExpr)
    tokens = self._GetTokens(node)
    _IncreasePenalty(tokens[1:], split_penalty.EXPR)

    return self.generic_visit(node)

  def visit_Dict(self, node):
    # Dict(keys=[Expr_1, Expr_2, ..., Expr_n],
    #      values=[Expr_1, Expr_2, ..., Expr_n])
    tokens = self._GetTokens(node)

    # The keys should be on a single line if at all possible.
    for key in node.keys:
      subrange = pyutils.GetTokensInSubRange(tokens, key)
      _IncreasePenalty(subrange[1:], split_penalty.DICT_KEY_EXPR)

    for value in node.values:
      subrange = pyutils.GetTokensInSubRange(tokens, value)
      _IncreasePenalty(subrange[1:], split_penalty.DICT_VALUE_EXPR)

    return self.generic_visit(node)

  def visit_Set(self, node):
    # Set(elts=[Expr_1, Expr_2, ..., Expr_n])
    tokens = self._GetTokens(node)
    for element in node.elts:
      subrange = pyutils.GetTokensInSubRange(tokens, element)
      _IncreasePenalty(subrange[1:], split_penalty.EXPR)

    return self.generic_visit(node)

  def visit_ListComp(self, node):
    # ListComp(elt=Expr,
    #          generators=[
    #              comprehension(
    #                  target=Expr,
    #                  iter=Expr,
    #                  ifs=[Expr_1, Expr_2, ..., Expr_n],
    #                  is_async=0),
    #               ...
    #          ])
    tokens = self._GetTokens(node)
    element = pyutils.GetTokensInSubRange(tokens, node.elt)
    _IncreasePenalty(element[1:], split_penalty.EXPR)

    for comp in node.generators:
      subrange = pyutils.GetTokensInSubRange(tokens, comp.iter)
      _IncreasePenalty(subrange[1:], split_penalty.EXPR)

      for if_expr in comp.ifs:
        subrange = pyutils.GetTokensInSubRange(tokens, if_expr)
        _IncreasePenalty(subrange[1:], split_penalty.EXPR)

    return self.generic_visit(node)

  def visit_SetComp(self, node):
    # SetComp(elt=Expr,
    #         generators=[
    #             comprehension(
    #                 target=Expr,
    #                 iter=Expr,
    #                 ifs=[Expr_1, Expr_2, ..., Expr_n],
    #                 is_async=0),
    #           ...
    #         ])
    tokens = self._GetTokens(node)
    element = pyutils.GetTokensInSubRange(tokens, node.elt)
    _IncreasePenalty(element[1:], split_penalty.EXPR)

    for comp in node.generators:
      subrange = pyutils.GetTokensInSubRange(tokens, comp.iter)
      _IncreasePenalty(subrange[1:], split_penalty.EXPR)

      for if_expr in comp.ifs:
        subrange = pyutils.GetTokensInSubRange(tokens, if_expr)
        _IncreasePenalty(subrange[1:], split_penalty.EXPR)

    return self.generic_visit(node)

  def visit_DictComp(self, node):
    # DictComp(key=KeyExpr,
    #          value=ValExpr,
    #          generators=[
    #              comprehension(
    #                  target=TargetExpr
    #                  iter=IterExpr,
    #                  ifs=[Expr_1, Expr_2, ..., Expr_n]),
    #                  is_async=0)],
    #           ...
    #         ])
    tokens = self._GetTokens(node)
    key = pyutils.GetTokensInSubRange(tokens, node.key)
    _IncreasePenalty(key[1:], split_penalty.EXPR)

    value = pyutils.GetTokensInSubRange(tokens, node.value)
    _IncreasePenalty(value[1:], split_penalty.EXPR)

    for comp in node.generators:
      subrange = pyutils.GetTokensInSubRange(tokens, comp.iter)
      _IncreasePenalty(subrange[1:], split_penalty.EXPR)

      for if_expr in comp.ifs:
        subrange = pyutils.GetTokensInSubRange(tokens, if_expr)
        _IncreasePenalty(subrange[1:], split_penalty.EXPR)

    return self.generic_visit(node)

  def visit_GeneratorExp(self, node):
    # GeneratorExp(elt=Expr,
    #              generators=[
    #                  comprehension(
    #                      target=Expr,
    #                      iter=Expr,
    #                      ifs=[Expr_1, Expr_2, ..., Expr_n],
    #                      is_async=0),
    #                ...
    #              ])
    tokens = self._GetTokens(node)
    element = pyutils.GetTokensInSubRange(tokens, node.elt)
    _IncreasePenalty(element[1:], split_penalty.EXPR)

    for comp in node.generators:
      subrange = pyutils.GetTokensInSubRange(tokens, comp.iter)
      _IncreasePenalty(subrange[1:], split_penalty.EXPR)

      for if_expr in comp.ifs:
        subrange = pyutils.GetTokensInSubRange(tokens, if_expr)
        _IncreasePenalty(subrange[1:], split_penalty.EXPR)

    return self.generic_visit(node)

  def visit_Await(self, node):
    # Await(value=Expr)
    tokens = self._GetTokens(node)
    _IncreasePenalty(tokens[1:], split_penalty.EXPR)

    return self.generic_visit(node)

  def visit_Yield(self, node):
    # Yield(value=Expr)
    tokens = self._GetTokens(node)
    _IncreasePenalty(tokens[1:], split_penalty.EXPR)

    return self.generic_visit(node)

  def visit_YieldFrom(self, node):
    # YieldFrom(value=Expr)
    tokens = self._GetTokens(node)
    _IncreasePenalty(tokens[1:], split_penalty.EXPR)
    tokens[2].split_penalty = split_penalty.UNBREAKABLE

    return self.generic_visit(node)

  def visit_Compare(self, node):
    # Compare(left=LExpr,
    #         ops=[Op_1, Op_2, ..., Op_n],
    #         comparators=[Expr_1, Expr_2, ..., Expr_n])
    tokens = self._GetTokens(node)
    _IncreasePenalty(tokens[1:], split_penalty.EXPR)

    operator_indices = [
        pyutils.GetNextTokenIndex(tokens, pyutils.TokenEnd(node.left))
    ] + [
        pyutils.GetNextTokenIndex(tokens, pyutils.TokenEnd(comparator))
        for comparator in node.comparators[:-1]
    ]
    split_before = style.Get('SPLIT_BEFORE_ARITHMETIC_OPERATOR')

    for operator_index in operator_indices:
      if not split_before:
        operator_index += 1
      _DecreasePenalty(tokens[operator_index], split_penalty.EXPR * 2)

    return self.generic_visit(node)

  def visit_Call(self, node):
    # Call(func=Expr,
    #      args=[Expr_1, Expr_2, ..., Expr_n],
    #      keywords=[
    #          keyword(
    #              arg='d',
    #              value=Expr),
    #            ...
    #      ])
    tokens = self._GetTokens(node)

    # Don't never split before the opening parenthesis.
    paren_index = pyutils.GetNextTokenIndex(tokens, pyutils.TokenEnd(node.func))
    _IncreasePenalty(tokens[paren_index], split_penalty.UNBREAKABLE)

    for arg in node.args:
      subrange = pyutils.GetTokensInSubRange(tokens, arg)
      _IncreasePenalty(subrange[1:], split_penalty.EXPR)

    return self.generic_visit(node)

  def visit_FormattedValue(self, node):
    # FormattedValue(value=Expr,
    #                conversion=-1)
    return node  # Ignore formatted values.

  def visit_JoinedStr(self, node):
    # JoinedStr(values=[Expr_1, Expr_2, ..., Expr_n])
    return self.generic_visit(node)

  def visit_Constant(self, node):
    # Constant(value=Expr)
    return self.generic_visit(node)

  def visit_Attribute(self, node):
    # Attribute(value=Expr,
    #           attr=Identifier)
    tokens = self._GetTokens(node)
    split_before = style.Get('SPLIT_BEFORE_DOT')
    dot_indices = pyutils.GetNextTokenIndex(tokens,
                                            pyutils.TokenEnd(node.value))

    if not split_before:
      dot_indices += 1
    _IncreasePenalty(tokens[dot_indices], split_penalty.VERY_STRONGLY_CONNECTED)

    return self.generic_visit(node)

  def visit_Subscript(self, node):
    # Subscript(value=ValueExpr,
    #           slice=SliceExpr)
    tokens = self._GetTokens(node)

    # Don't split before the opening bracket of a subscript.
    bracket_index = pyutils.GetNextTokenIndex(tokens,
                                              pyutils.TokenEnd(node.value))
    _IncreasePenalty(tokens[bracket_index], split_penalty.UNBREAKABLE)

    return self.generic_visit(node)

  def visit_Starred(self, node):
    # Starred(value=Expr)
    return self.generic_visit(node)

  def visit_Name(self, node):
    # Name(id=Identifier)
    tokens = self._GetTokens(node)
    _IncreasePenalty(tokens[1:], split_penalty.UNBREAKABLE)

    return self.generic_visit(node)

  def visit_List(self, node):
    # List(elts=[Expr_1, Expr_2, ..., Expr_n])
    tokens = self._GetTokens(node)

    for element in node.elts:
      subrange = pyutils.GetTokensInSubRange(tokens, element)
      _IncreasePenalty(subrange[1:], split_penalty.EXPR)
      _DecreasePenalty(subrange[0], split_penalty.EXPR // 2)

    return self.generic_visit(node)

  def visit_Tuple(self, node):
    # Tuple(elts=[Expr_1, Expr_2, ..., Expr_n])
    tokens = self._GetTokens(node)

    for element in node.elts:
      subrange = pyutils.GetTokensInSubRange(tokens, element)
      _IncreasePenalty(subrange[1:], split_penalty.EXPR)
      _DecreasePenalty(subrange[0], split_penalty.EXPR // 2)

    return self.generic_visit(node)

  def visit_Slice(self, node):
    # Slice(lower=Expr,
    #       upper=Expr,
    #       step=Expr)
    tokens = self._GetTokens(node)

    if hasattr(node, 'lower') and node.lower:
      subrange = pyutils.GetTokensInSubRange(tokens, node.lower)
      _IncreasePenalty(subrange, split_penalty.EXPR)
      _DecreasePenalty(subrange[0], split_penalty.EXPR // 2)

    if hasattr(node, 'upper') and node.upper:
      colon_index = pyutils.GetPrevTokenIndex(tokens,
                                              pyutils.TokenStart(node.upper))
      _IncreasePenalty(tokens[colon_index], split_penalty.UNBREAKABLE)
      subrange = pyutils.GetTokensInSubRange(tokens, node.upper)
      _IncreasePenalty(subrange, split_penalty.EXPR)
      _DecreasePenalty(subrange[0], split_penalty.EXPR // 2)

    if hasattr(node, 'step') and node.step:
      colon_index = pyutils.GetPrevTokenIndex(tokens,
                                              pyutils.TokenStart(node.step))
      _IncreasePenalty(tokens[colon_index], split_penalty.UNBREAKABLE)
      subrange = pyutils.GetTokensInSubRange(tokens, node.step)
      _IncreasePenalty(subrange, split_penalty.EXPR)
      _DecreasePenalty(subrange[0], split_penalty.EXPR // 2)

    return self.generic_visit(node)

  ############################################################################
  # Expression Context                                                       #
  ############################################################################

  def visit_Load(self, node):
    # Load()
    return self.generic_visit(node)

  def visit_Store(self, node):
    # Store()
    return self.generic_visit(node)

  def visit_Del(self, node):
    # Del()
    return self.generic_visit(node)

  ############################################################################
  # Boolean Operators                                                        #
  ############################################################################

  def visit_And(self, node):
    # And()
    return self.generic_visit(node)

  def visit_Or(self, node):
    # Or()
    return self.generic_visit(node)

  ############################################################################
  # Binary Operators                                                         #
  ############################################################################

  def visit_Add(self, node):
    # Add()
    return self.generic_visit(node)

  def visit_Sub(self, node):
    # Sub()
    return self.generic_visit(node)

  def visit_Mult(self, node):
    # Mult()
    return self.generic_visit(node)

  def visit_MatMult(self, node):
    # MatMult()
    return self.generic_visit(node)

  def visit_Div(self, node):
    # Div()
    return self.generic_visit(node)

  def visit_Mod(self, node):
    # Mod()
    return self.generic_visit(node)

  def visit_Pow(self, node):
    # Pow()
    return self.generic_visit(node)

  def visit_LShift(self, node):
    # LShift()
    return self.generic_visit(node)

  def visit_RShift(self, node):
    # RShift()
    return self.generic_visit(node)

  def visit_BitOr(self, node):
    # BitOr()
    return self.generic_visit(node)

  def visit_BitXor(self, node):
    # BitXor()
    return self.generic_visit(node)

  def visit_BitAnd(self, node):
    # BitAnd()
    return self.generic_visit(node)

  def visit_FloorDiv(self, node):
    # FloorDiv()
    return self.generic_visit(node)

  ############################################################################
  # Unary Operators                                                          #
  ############################################################################

  def visit_Invert(self, node):
    # Invert()
    return self.generic_visit(node)

  def visit_Not(self, node):
    # Not()
    return self.generic_visit(node)

  def visit_UAdd(self, node):
    # UAdd()
    return self.generic_visit(node)

  def visit_USub(self, node):
    # USub()
    return self.generic_visit(node)

  ############################################################################
  # Comparison Operators                                                     #
  ############################################################################

  def visit_Eq(self, node):
    # Eq()
    return self.generic_visit(node)

  def visit_NotEq(self, node):
    # NotEq()
    return self.generic_visit(node)

  def visit_Lt(self, node):
    # Lt()
    return self.generic_visit(node)

  def visit_LtE(self, node):
    # LtE()
    return self.generic_visit(node)

  def visit_Gt(self, node):
    # Gt()
    return self.generic_visit(node)

  def visit_GtE(self, node):
    # GtE()
    return self.generic_visit(node)

  def visit_Is(self, node):
    # Is()
    return self.generic_visit(node)

  def visit_IsNot(self, node):
    # IsNot()
    return self.generic_visit(node)

  def visit_In(self, node):
    # In()
    return self.generic_visit(node)

  def visit_NotIn(self, node):
    # NotIn()
    return self.generic_visit(node)

  ############################################################################
  # Exception Handler                                                        #
  ############################################################################

  def visit_ExceptionHandler(self, node):
    # ExceptHandler(type=Expr,
    #               name=Identifier,
    #               body=[...])
    return self.generic_visit(node)

  ############################################################################
  # Matching Patterns                                                        #
  ############################################################################

  def visit_MatchValue(self, node):
    # MatchValue(value=Expr)
    return self.generic_visit(node)

  def visit_MatchSingleton(self, node):
    # MatchSingleton(value=Constant)
    return self.generic_visit(node)

  def visit_MatchSequence(self, node):
    # MatchSequence(patterns=[pattern_1, pattern_2, ..., pattern_n])
    return self.generic_visit(node)

  def visit_MatchMapping(self, node):
    # MatchMapping(keys=[Expr_1, Expr_2, ..., Expr_n],
    #              patterns=[pattern_1, pattern_2, ..., pattern_m],
    #              rest=Identifier)
    return self.generic_visit(node)

  def visit_MatchClass(self, node):
    # MatchClass(cls=Expr,
    #            patterns=[pattern_1, pattern_2, ...],
    #            kwd_attrs=[Identifier_1, Identifier_2, ...],
    #            kwd_patterns=[pattern_1, pattern_2, ...])
    return self.generic_visit(node)

  def visit_MatchStar(self, node):
    # MatchStar(name=Identifier)
    return self.generic_visit(node)

  def visit_MatchAs(self, node):
    # MatchAs(pattern=pattern,
    #         name=Identifier)
    return self.generic_visit(node)

  def visit_MatchOr(self, node):
    # MatchOr(patterns=[pattern_1, pattern_2, ...])
    return self.generic_visit(node)

  ############################################################################
  # Type Ignore                                                              #
  ############################################################################

  def visit_TypeIgnore(self, node):
    # TypeIgnore(tag=string)
    return self.generic_visit(node)

  ############################################################################
  # Miscellaneous                                                            #
  ############################################################################

  def visit_comprehension(self, node):
    # comprehension(target=Expr,
    #               iter=Expr,
    #               ifs=[Expr_1, Expr_2, ..., Expr_n],
    #               is_async=0)
    return self.generic_visit(node)

  def visit_arguments(self, node):
    # arguments(posonlyargs=[arg_1, arg_2, ..., arg_a],
    #           args=[arg_1, arg_2, ..., arg_b],
    #           vararg=arg,
    #           kwonlyargs=[arg_1, arg_2, ..., arg_c],
    #           kw_defaults=[arg_1, arg_2, ..., arg_d],
    #           kwarg=arg,
    #           defaults=[Expr_1, Expr_2, ..., Expr_n])
    return self.generic_visit(node)

  def visit_arg(self, node):
    # arg(arg=Identifier,
    #     annotation=Expr,
    #     type_comment='')
    tokens = self._GetTokens(node)

    # Process any annotations.
    if hasattr(node, 'annotation') and node.annotation:
      annotation = node.annotation
      subrange = pyutils.GetTokensInSubRange(tokens, annotation)
      _IncreasePenalty(subrange, split_penalty.ANNOTATION)

    return self.generic_visit(node)

  def visit_keyword(self, node):
    # keyword(arg=Identifier,
    #         value=Expr)
    return self.generic_visit(node)

  def visit_alias(self, node):
    # alias(name=Identifier,
    #       asname=Identifier)
    return self.generic_visit(node)

  def visit_withitem(self, node):
    # withitem(context_expr=Expr,
    #          optional_vars=Expr)
    return self.generic_visit(node)

  def visit_match_case(self, node):
    # match_case(pattern=pattern,
    #            guard=Expr,
    #            body=[...])
    return self.generic_visit(node)


def _IncreasePenalty(tokens, amt):
  if not isinstance(tokens, list):
    tokens = [tokens]
  for token in tokens:
    token.split_penalty += amt


def _DecreasePenalty(tokens, amt):
  if not isinstance(tokens, list):
    tokens = [tokens]
  for token in tokens:
    token.split_penalty -= amt


def _SetPenalty(tokens, amt):
  if not isinstance(tokens, list):
    tokens = [tokens]
  for token in tokens:
    token.split_penalty = amt
