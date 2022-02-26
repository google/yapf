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
"""PyParser-related utilities.

This module collects various utilities related to the parse trees produced by
the pyparser.

  FindTokensInRange: produces a list of tokens from the logical lines within a
    range.
  GetTokensInSubRange: produces a sublist of tokens from a current token list
    within a range.
  GetTokenIndex: Get the index of a token.
  GetNextTokenIndex: Get the index of the next token after a given position.
  GetPrevTokenIndex: Get the index of the previous token before a given
    position.
  TokenStart: Convenience function to return the token's start as a tuple.
  TokenEnd: Convenience function to return the token's end as a tuple.
"""


def FindTokensInRange(logical_lines, node):
  """Get a list of tokens within the range [start, end)."""
  start = (node.lineno, node.col_offset)
  end = (node.end_lineno, node.end_col_offset)
  tokens = []
  for line in logical_lines:
    if line.start > end:
      break
    if line.start <= start or line.end >= end:
      tokens.extend(GetTokensInSubRange(line.tokens, start, end))
  return tokens


def GetTokensInSubRange(tokens, start, end):
  """Get a subset of tokens within the range [start, end)."""
  tokens_in_range = []
  for tok in tokens:
    tok_range = (tok.lineno, tok.column)
    if tok_range >= start and tok_range < end:
      tokens_in_range.append(tok)
  return tokens_in_range


def GetTokenIndex(tokens, pos):
  """Get the index of the token at 'pos.'"""
  index = 0
  while index < len(tokens):
    if (tokens[index].lineno, tokens[index].column) == pos:
      break
    index += 1
  return index


def GetNextTokenIndex(tokens, pos):
  """Get the index of the next token after 'pos.'"""
  index = 0
  while index < len(tokens):
    if (tokens[index].lineno, tokens[index].column) >= pos:
      break
    index += 1
  return index


def GetPrevTokenIndex(tokens, pos):
  """Get the index of the previous token before 'pos.'"""
  index = 1
  while index < len(tokens):
    if (tokens[index].lineno, tokens[index].column) >= pos:
      break
    index += 1
  return index - 1


def TokenStart(node):
  return (node.lineno, node.col_offset)


def TokenEnd(node):
  return (node.end_lineno, node.end_col_offset)


def AstDump(node):
  """Debugging code."""
  import ast
  print(ast.dump(node, include_attributes=True, indent=4))
