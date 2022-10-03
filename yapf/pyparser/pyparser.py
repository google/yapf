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
"""Simple Python Parser

Parse Python code into a list of logical lines, represented by LogicalLine
objects. This uses Python's tokenizer to generate the tokens. As such, YAPF must
be run with the appropriate Python version---Python 2.7 for Python2 code, Python
3.x for Python3 code, etc.

This parser uses Python's native "tokenizer" module to generate a list of tokens
for the source code. It then uses Python's native "ast" module to assign
subtypes, calculate split penalties, etc.

A "logical line" produced by Python's "tokenizer" module ends with a
tokenize.NEWLINE, rather than a tokenize.NL, making it easy to separate them
out.

  ParseCode(): parse the code producing a list of logical lines.
"""

# TODO: Call from yapf_api.FormatCode.

import ast
import os
import token
import tokenize

from yapf.pyparser import split_penalty_visitor
from yapf.yapflib import format_token
from yapf.yapflib import logical_line
from yapf.yapflib import py3compat
from yapf.yapflib import style
from yapf.yapflib import subtypes

CONTINUATION = token.N_TOKENS


def ParseCode(unformatted_source, filename='<unknown>'):
  """Parse a string of Python code into logical lines.

  This provides an alternative entry point to YAPF.

  Arguments:
    unformatted_source: (unicode) The code to format.
    filename: (unicode) The name of the file being reformatted.

  Returns:
    A list of LogicalLines.

  Raises:
    An exception is raised if there's an error during AST parsing.
  """
  if not unformatted_source.endswith(os.linesep):
    unformatted_source += os.linesep

  try:
    ast_tree = ast.parse(unformatted_source, filename)
    ast.fix_missing_locations(ast_tree)
    readline = py3compat.StringIO(unformatted_source).readline
    tokens   = tokenize.generate_tokens(readline)
  except Exception:
    raise

  logical_lines = _CreateLogicalLines(tokens)

  # Process the logical lines.
  split_penalty_visitor.SplitPenalty(logical_lines).visit(ast_tree)

  return logical_lines


def _CreateLogicalLines(tokens):
  """Separate tokens into logical lines.

  Arguments:
    tokens: (list of tokenizer.TokenInfo) Tokens generated by tokenizer.

  Returns:
    A list of LogicalLines.
  """
  logical_lines    = []
  cur_logical_line = []
  prev_tok         = None
  depth            = 0

  for tok in tokens:
    tok = py3compat.TokenInfo(*tok)
    if tok.type == tokenize.NEWLINE:
      # End of a logical line.
      logical_lines.append(logical_line.LogicalLine(depth, cur_logical_line))
      cur_logical_line = []
      prev_tok         = None
    elif tok.type == tokenize.INDENT:
      depth += 1
    elif tok.type == tokenize.DEDENT:
      depth -= 1
    elif tok.type not in {tokenize.NL, tokenize.ENDMARKER}:
      if (prev_tok and prev_tok.line.rstrip().endswith('\\') and
          prev_tok.start[0] < tok.start[0]):
        # Insert a token for a line continuation.
        ctok = py3compat.TokenInfo(
            type   =CONTINUATION,
            string ='\\',
            start  =(prev_tok.start[0], prev_tok.start[1] + 1),
            end    =(prev_tok.end[0], prev_tok.end[0] + 2),
            line   =prev_tok.line)
        ctok.lineno = ctok.start[0]
        ctok.column = ctok.start[1]
        ctok.value  = '\\'
        cur_logical_line.append(format_token.FormatToken(ctok, 'CONTINUATION'))
      tok.lineno = tok.start[0]
      tok.column = tok.start[1]
      tok.value  = tok.string
      cur_logical_line.append(
          format_token.FormatToken(tok, token.tok_name[tok.type]))
    prev_tok = tok

  # Link the FormatTokens in each line together to for a doubly linked list.
  for line in logical_lines:
    previous      = line.first
    bracket_stack = [previous] if previous.OpensScope() else []
    for tok in line.tokens[1:]:
      tok.previous_token  = previous
      previous.next_token = tok
      previous            = tok

      # Set up the "matching_bracket" attribute.
      if tok.OpensScope():
        bracket_stack.append(tok)
      elif tok.ClosesScope():
        bracket_stack[-1].matching_bracket = tok
        tok.matching_bracket               = bracket_stack.pop()

  return logical_lines
