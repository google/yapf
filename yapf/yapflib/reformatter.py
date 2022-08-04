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

The `logical_line.LogicalLine`s are now ready to be formatted. LogicalLInes that
can be merged together are. The best formatting is returned as a string.

  Reformat(): the main function exported by this module.
"""

from __future__ import unicode_literals

import collections
from distutils.errors import LinkError
import heapq
import re

from lib2to3 import pytree
from lib2to3.pgen2 import token

from yapf.pytree import pytree_utils
from yapf.yapflib import format_decision_state
from yapf.yapflib import format_token
from yapf.yapflib import line_joiner
from yapf.yapflib import style
from yapf.yapflib import verifier


def Reformat(llines, verify=False, lines=None):
  """Reformat the logical lines.

  Arguments:
    llines: (list of logical_line.LogicalLine) Lines we want to format.
    verify: (bool) True if reformatted code should be verified for syntax.
    lines: (set of int) The lines which can be modified or None if there is no
      line range restriction.

  Returns:
    A string representing the reformatted code.
  """
  final_lines = []
  prev_line = None  # The previous line.
  indent_width = style.Get('INDENT_WIDTH')

  for lline in _SingleOrMergedLines(llines):
    first_token = lline.first
    _FormatFirstToken(first_token, lline.depth, prev_line, final_lines)

    indent_amt = indent_width * lline.depth
    state = format_decision_state.FormatDecisionState(lline, indent_amt)
    state.MoveStateToNextToken()

    if not lline.disable:
      if lline.first.is_comment:
        lline.first.value = lline.first.value.rstrip()
      elif lline.last.is_comment:
        lline.last.value = lline.last.value.rstrip()
      if prev_line and prev_line.disable:
        # Keep the vertical spacing between a disabled and enabled formatting
        # region.
        _RetainRequiredVerticalSpacingBetweenTokens(lline.first, prev_line.last,
                                                    lines)
      if any(tok.is_comment for tok in lline.tokens):
        _RetainVerticalSpacingBeforeComments(lline)

    if lline.disable or _LineHasContinuationMarkers(lline):
      _RetainHorizontalSpacing(lline)
      _RetainRequiredVerticalSpacing(lline, prev_line, lines)
      _EmitLineUnformatted(state)

    elif (_LineContainsPylintDisableLineTooLong(lline) or
          _LineContainsI18n(lline)):
      # Don't modify vertical spacing, but fix any horizontal spacing issues.
      _RetainRequiredVerticalSpacing(lline, prev_line, lines)
      _EmitLineUnformatted(state)

    elif _CanPlaceOnSingleLine(lline) and not any(tok.must_break_before
                                                  for tok in lline.tokens):
      # The logical line fits on one line.
      while state.next_token:
        state.AddTokenToState(newline=False, dry_run=False)

    elif not _AnalyzeSolutionSpace(state):
      # Failsafe mode. If there isn't a solution to the line, then just emit
      # it as is.
      state = format_decision_state.FormatDecisionState(lline, indent_amt)
      state.MoveStateToNextToken()
      _RetainHorizontalSpacing(lline)
      _RetainRequiredVerticalSpacing(lline, prev_line, None)
      _EmitLineUnformatted(state)

    final_lines.append(lline)
    prev_line = lline


  """Xiao's alignment implementation"""
  if style.Get('ALIGN_ASSIGNMENT'):
    _AlignAssignment(final_lines)
  if (style.Get('EACH_DICT_ENTRY_ON_SEPARATE_LINE') and style.Get('DEDENT_CLOSING_BRACKETS')
    and style.Get('ALIGN_DICT_COLON')):
    _AlignDictColon(final_lines)
  if style.Get('DEDENT_CLOSING_BRACKETS') and style.Get('ALIGN_ARGUMENT_ASSIGNMENT'):
    _AlignArgAssign(final_lines)

  _AlignTrailingComments(final_lines)
  return _FormatFinalLines(final_lines, verify)


def _RetainHorizontalSpacing(line):
  """Retain all horizontal spacing between tokens."""
  for tok in line.tokens:
    tok.RetainHorizontalSpacing(line.first.column, line.depth)


def _RetainRequiredVerticalSpacing(cur_line, prev_line, lines):
  """Retain all vertical spacing between lines."""
  prev_tok = None
  if prev_line is not None:
    prev_tok = prev_line.last

  if cur_line.disable:
    # After the first token we are acting on a single line. So if it is
    # disabled we must not reformat.
    lines = set()

  for cur_tok in cur_line.tokens:
    _RetainRequiredVerticalSpacingBetweenTokens(cur_tok, prev_tok, lines)
    prev_tok = cur_tok


def _RetainRequiredVerticalSpacingBetweenTokens(cur_tok, prev_tok, lines):
  """Retain vertical spacing between two tokens if not in editable range."""
  if prev_tok is None:
    return

  if prev_tok.is_string:
    prev_lineno = prev_tok.lineno + prev_tok.value.count('\n')
  elif prev_tok.is_pseudo:
    if not prev_tok.previous_token.is_multiline_string:
      prev_lineno = prev_tok.previous_token.lineno
    else:
      prev_lineno = prev_tok.lineno
  else:
    prev_lineno = prev_tok.lineno

  if cur_tok.is_comment:
    cur_lineno = cur_tok.lineno - cur_tok.value.count('\n')
  else:
    cur_lineno = cur_tok.lineno

  if not prev_tok.is_comment and prev_tok.value.endswith('\\'):
    prev_lineno += prev_tok.value.count('\n')

  required_newlines = cur_lineno - prev_lineno
  if cur_tok.is_comment and not prev_tok.is_comment:
    # Don't adjust between a comment and non-comment.
    pass
  elif lines and lines.intersection(range(prev_lineno, cur_lineno + 1)):
    desired_newlines = cur_tok.whitespace_prefix.count('\n')
    whitespace_lines = range(prev_lineno + 1, cur_lineno)
    deletable_lines = len(lines.intersection(whitespace_lines))
    required_newlines = max(required_newlines - deletable_lines,
                            desired_newlines)

  cur_tok.AdjustNewlinesBefore(required_newlines)


def _RetainVerticalSpacingBeforeComments(line):
  """Retain vertical spacing before comments."""
  prev_token = None
  for tok in line.tokens:
    if tok.is_comment and prev_token:
      if tok.lineno - tok.value.count('\n') - prev_token.lineno > 1:
        tok.AdjustNewlinesBefore(ONE_BLANK_LINE)

    prev_token = tok


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
  while state.next_token:
    previous_token = state.next_token.previous_token
    previous_lineno = previous_token.lineno

    if previous_token.is_multiline_string or previous_token.is_string:
      previous_lineno += previous_token.value.count('\n')

    if previous_token.is_continuation:
      newline = False
    else:
      newline = state.next_token.lineno > previous_lineno

    state.AddTokenToState(newline=newline, dry_run=False)


def _LineContainsI18n(line):
  """Return true if there are i18n comments or function calls in the line.

  I18n comments and pseudo-function calls are closely related. They cannot
  be moved apart without breaking i18n.

  Arguments:
    line: (logical_line.LogicalLine) The line currently being formatted.

  Returns:
    True if the line contains i18n comments or function calls. False otherwise.
  """
  if style.Get('I18N_COMMENT'):
    for tok in line.tokens:
      if tok.is_comment and re.match(style.Get('I18N_COMMENT'), tok.value):
        # Contains an i18n comment.
        return True

  if style.Get('I18N_FUNCTION_CALL'):
    length = len(line.tokens)
    for index in range(length - 1):
      if (line.tokens[index + 1].value == '(' and
          line.tokens[index].value in style.Get('I18N_FUNCTION_CALL')):
        return True
  return False


def _LineContainsPylintDisableLineTooLong(line):
  """Return true if there is a "pylint: disable=line-too-long" comment."""
  return re.search(r'\bpylint:\s+disable=line-too-long\b', line.last.value)


def _LineHasContinuationMarkers(line):
  """Return true if the line has continuation markers in it."""
  return any(tok.is_continuation for tok in line.tokens)


def _CanPlaceOnSingleLine(line):
  """Determine if the logical line can go on a single line.

  Arguments:
    line: (logical_line.LogicalLine) The line currently being formatted.

  Returns:
    True if the line can or should be added to a single line. False otherwise.
  """
  token_names = [x.name for x in line.tokens]
  if (style.Get('FORCE_MULTILINE_DICT') and 'LBRACE' in token_names):
    return False
  indent_amt = style.Get('INDENT_WIDTH') * line.depth
  last = line.last
  last_index = -1
  if (last.is_pylint_comment or last.is_pytype_comment or
      last.is_copybara_comment):
    last = last.previous_token
    last_index = -2
  if last is None:
    return True
  return (last.total_length + indent_amt <= style.Get('COLUMN_LIMIT') and
          not any(tok.is_comment for tok in line.tokens[:last_index]))


def _AlignTrailingComments(final_lines):
  """Align trailing comments to the same column."""
  final_lines_index = 0
  while final_lines_index < len(final_lines):
    line = final_lines[final_lines_index]
    assert line.tokens
    processed_content = False

    for tok in line.tokens:
      if (isinstance(tok.spaces_required_before, list) and tok.is_comment and
          tok.value.startswith('#')):
        # All trailing comments
        # NOTE not including comments that appear on a line by themselves
        # in this block should be indented at the same level. The block is
        # terminated by an empty line or EOF. Enumerate through each line in
        # the block and calculate the max line length. Once complete, use the
        # first col value greater than that value and create the necessary for
        # each line accordingly.
        all_pc_line_lengths = []  # All pre-comment line lengths
        max_line_length = 0

        while True:
          # EOF
          if final_lines_index + len(all_pc_line_lengths) == len(final_lines):
            break

          this_line = final_lines[final_lines_index + len(all_pc_line_lengths)]

          # Blank line - note that content is preformatted so we don't need to
          # worry about spaces/tabs; a blank line will always be '\n\n'.
          assert this_line.tokens
          if (all_pc_line_lengths and
              this_line.tokens[0].formatted_whitespace_prefix.startswith('\n\n')
             ):
            break

          if this_line.disable:
            all_pc_line_lengths.append([])
            continue

          # Calculate the length of each line in this logical line.
          line_content = ''
          pc_line_lengths = []

          #NOTE added by Xiao
          contain_object = False
          for line_tok in this_line.tokens:

            #NOTE-------------- added by Xiao----------------------------
            if (line_tok.value in [')', ']','}']
              and line_tok.formatted_whitespace_prefix.startswith('\n')):
              contain_object = True
            #------------------------------------------------------------

            whitespace_prefix = line_tok.formatted_whitespace_prefix

            newline_index = whitespace_prefix.rfind('\n')
            if newline_index != -1:
              max_line_length = max(max_line_length, len(line_content))
              line_content = ''

              whitespace_prefix = whitespace_prefix[newline_index + 1:]

            # if comment starts with '\n', it will save length 0
            if line_tok.is_comment:
              pc_line_lengths.append(len(line_content))
            else:
              line_content += '{}{}'.format(whitespace_prefix, line_tok.value)

          if pc_line_lengths:
            max_line_length = max(max_line_length, max(pc_line_lengths))

          all_pc_line_lengths.append(pc_line_lengths)

          #NOTE---------------------added by Xiao-----------------
          # if it's a logical line with object(dict/list/tuple)
          # that have its items in separate lines
          if contain_object:
            break
          #-------------------------------------------------------
        # Calculate the aligned column value
        max_line_length += 2

        aligned_col = None
        for potential_col in tok.spaces_required_before:
          if potential_col > max_line_length:
            aligned_col = potential_col
            break

        if aligned_col is None:
          aligned_col = max_line_length

        # Update the comment token values based on the aligned values
        for all_pc_line_lengths_index, pc_line_lengths in enumerate(
            all_pc_line_lengths):
          if not pc_line_lengths:
            continue

          this_line = final_lines[final_lines_index + all_pc_line_lengths_index]

          pc_line_length_index = 0
          for line_tok in this_line.tokens:
            if line_tok.is_comment:
              assert pc_line_length_index < len(pc_line_lengths)
              assert pc_line_lengths[pc_line_length_index] < aligned_col

              # Note that there may be newlines embedded in the comments, so
              # we need to apply a whitespace prefix to each line.
              whitespace = ' ' * (
                  aligned_col - pc_line_lengths[pc_line_length_index] - 1)

              #NOTE--------------------------------------------------------------#
              ''' this is added by Xiao because we don't want comments on newlines
                  to align with comments inline
              '''
              if not style.Get('ALIGN_NEWLINE_COMMENTS_WITH_INLINE_COMMENTS'):
                # if this comment starts with '\n', pass and go to next comment
                if pc_line_lengths[pc_line_length_index] == 0:
                  pc_line_length_index += 1
                  continue
                line_content = '{}{}'.format(whitespace, line_tok.value.strip())
              else:
                line_content = []

                for comment_line_index, comment_line in enumerate(
                    line_tok.value.split('\n')):
                  line_content.append('{}{}'.format(whitespace,
                                                  comment_line.strip()))

                  if comment_line_index == 0:
                    whitespace = ' ' * (aligned_col - 1)

                line_content = '\n'.join(line_content)
              #----------------------------------------------------------------#
              # after process, go to next pre comment tokens length
              pc_line_length_index += 1

              # Account for initial whitespace already slated for the
              # beginning of the line.
              existing_whitespace_prefix = \
                line_tok.formatted_whitespace_prefix.lstrip('\n')

              if line_content.startswith(existing_whitespace_prefix):
                line_content = line_content[len(existing_whitespace_prefix):]

              line_tok.value = line_content

          assert pc_line_length_index == len(pc_line_lengths)

        final_lines_index += len(all_pc_line_lengths)

        processed_content = True
        break

    if not processed_content:
      final_lines_index += 1



#########################################################################


""" XIAO'S IMPLEMENTATION  """

def _AlignAssignment(final_lines):
  """Align assignment operators and augmented assignment operators to the same column"""

  final_lines_index = 0
  while final_lines_index < len(final_lines):
    line = final_lines[final_lines_index]

    assert line.tokens
    process_content = False

    for tok in line.tokens:
      if tok.is_assign or tok.is_augassign:
        # all pre assignment variable lengths in one block of lines
        all_pa_variables_lengths = []
        max_variables_length = 0

        while True:
            # EOF
          if final_lines_index + len(all_pa_variables_lengths) == len(final_lines):
            break

          this_line_index = final_lines_index + len(all_pa_variables_lengths)
          this_line = final_lines[this_line_index]

          next_line = None
          if this_line_index < len(final_lines) - 1:
            next_line = final_lines[final_lines_index + len(all_pa_variables_lengths) + 1 ]

          assert this_line.tokens, next_line.tokens

          # align them differently when there is a blank line in between
          if (all_pa_variables_lengths and
                this_line.tokens[0].formatted_whitespace_prefix.startswith('\n\n')
            ):
              break

          # if there is a standalone comment or keyword statement line
          # or other lines without assignment in between, break
          elif (all_pa_variables_lengths and
            True not in [tok.is_assign or tok.is_augassign for tok in this_line.tokens]):
            if this_line.tokens[0].is_comment:
              if style.Get('NEW_ALIGNMENT_AFTER_COMMENTLINE'):
                break
            else: break

          if this_line.disable:
            all_pa_variables_lengths.append([])
            continue

          variables_content = ''
          pa_variables_lengths = []
          contain_object = False
          # only one assignment expression is on each line
          for line_tok in this_line.tokens:
            prefix = line_tok.formatted_whitespace_prefix
            newline_index = prefix.rfind('\n')
            if newline_index != -1:
              variables_content = ''
              prefix = prefix[newline_index + 1:]

            if line_tok.is_assign or line_tok.is_augassign:
              next_tok = line_tok.next_token
              while next_tok and next_tok.value not in ['(', '[', '{']:
                next_tok = next_tok.next_token
              # if there is object(list/tuple/dict) with newline entries, break,
              # update the alignment so far and start to calulate new alignment
              if (next_tok and next_tok.value in ['(', '[', '{'] and
                next_tok.next_token.formatted_whitespace_prefix.startswith('\n')):
                pa_variables_lengths.append(len(variables_content))
                contain_object = True
              else:
                if line_tok.is_assign:
                  pa_variables_lengths.append(len(variables_content))
                # if augassign, add the extra augmented part to the max length caculation
                elif line_tok.is_augassign:
                  pa_variables_lengths.append(len(variables_content) + len(line_tok.value) - 1 )
                # don't add the tokens after the assignment operator
                break
            else:
              variables_content += '{}{}'.format(prefix, line_tok.value)

          if pa_variables_lengths:
            max_variables_length = max(max_variables_length, max(pa_variables_lengths))

          all_pa_variables_lengths.append(pa_variables_lengths)

          # after saving this line's max variable length,
          # we check if next line has the same depth as this line,
          # if not, we don't want to calculate their max variable length together
          # so we break the while loop, update alignment so far, and
          # then go to next line that has '='
          if next_line:
            if this_line.depth != next_line.depth:
              break
          # if this line contains objects with newline entries,
          # start new block alignment
          if contain_object:
            break

        # if no update of max_length, just go to the next block
        if max_variables_length == 0: continue

        max_variables_length += 2

        # Update the assignment token values based on the max variable length
        for all_pa_variables_lengths_index, pa_variables_lengths in enumerate(
                  all_pa_variables_lengths):
            if not pa_variables_lengths:
                continue
            this_line = final_lines[final_lines_index + all_pa_variables_lengths_index]

            # only the first assignment operator on each line
            pa_variables_lengths_index = 0
            for line_tok in this_line.tokens:
              if line_tok.is_assign or line_tok.is_augassign:
                assert pa_variables_lengths[0] < max_variables_length

                if pa_variables_lengths_index < len(pa_variables_lengths):
                  whitespace = ' ' * (
                  max_variables_length - pa_variables_lengths[0] - 1)

                  assign_content = '{}{}'.format(whitespace, line_tok.value.strip())

                  existing_whitespace_prefix = \
                      line_tok.formatted_whitespace_prefix.lstrip('\n')

                  # in case the existing spaces are larger than padded spaces
                  if (len(whitespace) == 1 or len(whitespace) > 1 and
                    len(existing_whitespace_prefix)>len(whitespace)):
                    line_tok.whitespace_prefix = ''
                  elif assign_content.startswith(existing_whitespace_prefix):
                      assign_content = assign_content[len(existing_whitespace_prefix):]

                  # update the assignment operator value
                  line_tok.value = assign_content

                pa_variables_lengths_index += 1

        final_lines_index += len(all_pa_variables_lengths)

        process_content = True
        break

    if not process_content:
        final_lines_index += 1


def _AlignArgAssign(final_lines):
  """Align the assign operators in a argument list to the same column"""
  """NOTE One argument list of one function is on one logical line!
     But funtion calls/argument lists can be in argument list.
  """
  #for l in final_lines:
    #for t in l.tokens:
      #print('token:', t.value, t.subtypes, t.is_comment, t.is_argname_start, t.is_argname)

  final_lines_index = 0
  while final_lines_index < len(final_lines):
    line = final_lines[final_lines_index]
    if line.disable:
      final_lines_index += 1
      continue

    assert line.tokens
    process_content = False

    for tok in line.tokens:
      if tok.is_argassign:

        this_line = line
        line_tokens = this_line.tokens

        for open_index in range(len(line_tokens)):
          line_tok = line_tokens[open_index]

          if (line_tok.value == '(' and not line_tok.is_pseudo
            and line_tok.next_token.formatted_whitespace_prefix.startswith('\n')):
            index = open_index
            # skip the comments in the beginning
            index += 1
            line_tok = line_tokens[index]
            while not line_tok.is_argname_start and index < len(line_tokens)-1:
              index += 1
              line_tok = line_tokens[index]

            # check if the argstart is on newline
            if line_tok.is_argname_start and line_tok.formatted_whitespace_prefix.startswith('\n'):
              first_arg_index = index
              first_arg_column = len(line_tok.formatted_whitespace_prefix.lstrip('\n'))

              closing = False
              all_arg_name_lengths = []
              arg_name_lengths = []
              name_content = ''
              arg_column = first_arg_column

              # start with the first argument
              # that has nextline prefix
              while not closing:
                # if there is a comment in between, save, reset and continue to calulate new alignment
                if (style.Get('NEW_ALIGNMENT_AFTER_COMMENTLINE')
                  and arg_name_lengths and line_tok.is_comment
                  and line_tok.formatted_whitespace_prefix.startswith('\n')):
                  all_arg_name_lengths.append(arg_name_lengths)
                  arg_name_lengths = []
                  index += 1
                  line_tok = line_tokens[index]
                  continue

                prefix = line_tok.formatted_whitespace_prefix
                newline_index = prefix.rfind('\n')

                if newline_index != -1:
                  if line_tok.is_argname_start:
                    name_content = ''
                    prefix = prefix[newline_index + 1:]
                    arg_column = len(prefix)
                # if any argument not on newline
                elif line_tok.is_argname_start:
                  name_content = ''
                  arg_column =  line_tok.column
                  # in case they are formatted into one line in final_line
                  # but are put in separated lines in original codes
                  if arg_column == first_arg_column:
                    arg_column = line_tok.formatted_whitespace_prefix
                # on the same argument level
                if (line_tok.is_argname_start and arg_name_lengths
                  and arg_column==first_arg_column):
                  argname_end = line_tok
                  while argname_end.is_argname:
                    argname_end = argname_end.next_token
                  # argument without assignment in between
                  if not argname_end.is_argassign:
                    all_arg_name_lengths.append(arg_name_lengths)
                    arg_name_lengths = []
                    index += 1
                    line_tok = line_tokens[index]
                    continue

                if line_tok.is_argassign and arg_column == first_arg_column:
                  arg_name_lengths.append(len(name_content))
                elif line_tok.is_argname and arg_column == first_arg_column:
                  name_content += '{}{}'.format(prefix, line_tok.value)
                  # add up all token values before the arg assign operator

                index += 1
                if index < len(line_tokens):
                  line_tok = line_tokens[index]

                # if there is a new object(list/tuple/dict) with its entries on newlines,
                # save, reset and continue to calulate new alignment
                if (line_tok.value in ['(', '[','{'] and line_tok.next_token
                  and line_tok.next_token.formatted_whitespace_prefix.startswith('\n')):
                  if arg_name_lengths:
                    all_arg_name_lengths.append(arg_name_lengths)
                  arg_name_lengths = []
                  index += 1
                  line_tok = line_tokens[index]
                  continue

                if line_tok.value == ')'and not line_tok.is_pseudo:
                  if line_tok.formatted_whitespace_prefix.startswith('\n'):
                    close_column = len(line_tok.formatted_whitespace_prefix.lstrip('\n'))
                  else: close_column = line_tok.column
                  if close_column < first_arg_column:
                    if arg_name_lengths:
                      all_arg_name_lengths.append(arg_name_lengths)
                    closing = True

              # update the alignment once one full arg list is processed
              if all_arg_name_lengths:
                # if argument list with only the first argument on newline
                if len(all_arg_name_lengths) == 1 and len(all_arg_name_lengths[0]) == 1:
                  continue
                max_name_length = 0
                all_arg_name_lengths_index = 0
                arg_name_lengths = all_arg_name_lengths[all_arg_name_lengths_index]
                max_name_length = max(arg_name_lengths or [0]) + 2
                arg_lengths_index = 0
                for token in line_tokens[first_arg_index:index]:
                  if token.is_argassign:
                    name_token = token.previous_token
                    while name_token.is_argname and not name_token.is_argname_start:
                      name_token = name_token.previous_token
                    name_column = len(name_token.formatted_whitespace_prefix.lstrip('\n'))
                    if name_column == first_arg_column:
                      if all_arg_name_lengths_index < len(all_arg_name_lengths):
                        if arg_lengths_index == len(arg_name_lengths):
                          all_arg_name_lengths_index += 1
                          arg_name_lengths = all_arg_name_lengths[all_arg_name_lengths_index]
                          max_name_length = max(arg_name_lengths or [0]) + 2
                          arg_lengths_index = 0

                        if arg_lengths_index < len(arg_name_lengths):

                          assert arg_name_lengths[arg_lengths_index] < max_name_length

                          padded_spaces = ' ' * (
                            max_name_length - arg_name_lengths[arg_lengths_index] - 1)
                          arg_lengths_index += 1

                          assign_content = '{}{}'.format(padded_spaces, token.value.strip())
                          existing_whitespace_prefix = \
                                token.formatted_whitespace_prefix.lstrip('\n')

                          # in case the existing spaces are larger than padded spaces
                          if (len(padded_spaces)==1 or len(padded_spaces)>1 and
                            len(existing_whitespace_prefix)>len(padded_spaces)):
                            token.whitespace_prefix = ''
                          elif assign_content.startswith(existing_whitespace_prefix):
                            assign_content = assign_content[len(existing_whitespace_prefix):]

                          token.value = assign_content

        final_lines_index += 1
        process_content = True
        break

    if not process_content:
      final_lines_index += 1


def _AlignDictColon(final_lines):
  """Align colons in a dict to the same column"""
  """NOTE One (nested) dict/list is one logical line!"""
  final_lines_index = 0
  while final_lines_index < len(final_lines):
    line = final_lines[final_lines_index]
    if line.disable:
      final_lines_index += 1
      continue

    assert line.tokens
    process_content = False

    for tok in line.tokens:
      # make sure each dict entry on separate lines and
      # the dict has more than one entry
      if (tok.is_dict_key and tok.formatted_whitespace_prefix.startswith('\n') and
            not tok.is_comment):

            this_line = line

            line_tokens = this_line.tokens
            for open_index in range(len(line_tokens)):
              line_tok = line_tokens[open_index]

              # check each time if the detected dict is the dict we aim for
              if line_tok.value == '{' and line_tok.next_token.formatted_whitespace_prefix.startswith('\n'):
                index = open_index
                # skip the comments in the beginning
                index += 1
                line_tok = line_tokens[index]
                while not line_tok.is_dict_key and index < len(line_tokens)-1:
                  index += 1
                  line_tok = line_tokens[index]
                # in case empty dict, check if dict key again
                if line_tok.is_dict_key and line_tok.formatted_whitespace_prefix.startswith('\n'):
                  closing = False # the closing bracket in dict '}'.
                  keys_content = ''
                  all_dict_keys_lengths = []
                  dict_keys_lengths = []
                  index = open_index

                  # record the column number of the first key
                  first_key_column = len(line_tok.formatted_whitespace_prefix.lstrip('\n'))
                  key_column = first_key_column

                  # while not closing:
                  while not closing:
                    prefix = line_tok.formatted_whitespace_prefix
                    newline = prefix.startswith('\n')
                    if newline:
                      # if comments inbetween, save, reset and continue to caluclate new alignment
                      if (style.Get('NEW_ALIGNMENT_AFTER_COMMENTLINE')
                        and dict_keys_lengths and line_tok.is_comment):
                        all_dict_keys_lengths.append(dict_keys_lengths)
                        dict_keys_lengths =[]
                        index += 1
                        line_tok = line_tokens[index]
                        continue
                      if line_tok.is_dict_key:
                        keys_content = ''
                        prefix = prefix.lstrip('\n')
                        key_column = len(prefix)
                    elif line_tok.is_dict_key:
                      key_column = line_tok.column

                    if line_tok.is_dict_colon and key_column == first_key_column:
                      dict_keys_lengths.append(len(keys_content))
                    elif line_tok.is_dict_key and key_column == first_key_column:
                      keys_content += '{}{}'.format(prefix, line_tok.value)

                    index += 1
                    if index < len(line_tokens):
                      line_tok = line_tokens[index]

                    # if there is new objects(list/tuple/dict) with its entries on newlines,
                    # or a function call with any of its arguments on newlines,
                    # save, reset and continue to calulate new alignment
                    if (line_tok.value in ['(', '[', '{'] and not line_tok.is_pseudo and line_tok.next_token
                      and line_tok.next_token.formatted_whitespace_prefix.startswith('\n')):
                      if dict_keys_lengths:
                        all_dict_keys_lengths.append(dict_keys_lengths)
                      dict_keys_lengths = []
                      index += 1
                      line_tok = line_tokens[index]
                      continue
                    # the matching closing bracket is either same indented or dedented
                    # accordingly to previous level's indentation
                    # the first found, immediately break the while loop
                    if line_tok.value == '}':
                      if line_tok.formatted_whitespace_prefix.startswith('\n'):
                        close_column = len(line_tok.formatted_whitespace_prefix.lstrip('\n'))
                      else: close_column = line_tok.column
                      if close_column < first_key_column:
                        if dict_keys_lengths:
                          all_dict_keys_lengths.append(dict_keys_lengths)
                        closing = True

                  # update the alignment once one dict is processed
                  if all_dict_keys_lengths:
                    max_keys_length = 0
                    all_dict_keys_lengths_index = 0
                    dict_keys_lengths = all_dict_keys_lengths[all_dict_keys_lengths_index]
                    max_keys_length = max(dict_keys_lengths or [0]) + 2
                    keys_lengths_index = 0
                    for token in line_tokens[open_index+1:index]:
                      if token.is_dict_colon:
                        # check if the key has multiple tokens and
                        # get the first key token in this key
                        key_token = token.previous_token
                        while key_token.previous_token.is_dict_key:
                          key_token = key_token.previous_token
                        key_column = len(key_token.formatted_whitespace_prefix.lstrip('\n'))

                        if key_column == first_key_column:

                          if keys_lengths_index == len(dict_keys_lengths):
                            all_dict_keys_lengths_index += 1
                            dict_keys_lengths = all_dict_keys_lengths[all_dict_keys_lengths_index]
                            max_keys_length = max(dict_keys_lengths or [0]) + 2
                            keys_lengths_index = 0

                          if keys_lengths_index < len(dict_keys_lengths):
                            assert dict_keys_lengths[keys_lengths_index] < max_keys_length

                            padded_spaces = ' ' * (
                              max_keys_length - dict_keys_lengths[keys_lengths_index] - 1)
                            keys_lengths_index += 1
                            #TODO if the existing whitespaces are larger than padded spaces
                            existing_whitespace_prefix = \
                                  token.formatted_whitespace_prefix.lstrip('\n')
                            colon_content = '{}{}'.format(padded_spaces, token.value.strip())

                            # in case the existing spaces are larger than the paddes spaces
                            if (len(padded_spaces) == 0 or len(padded_spaces) > 0
                              and len(existing_whitespace_prefix) >= len(padded_spaces)):
                              # remove the existing spaces
                              token.whitespace_prefix = ''
                            elif colon_content.startswith(existing_whitespace_prefix):
                              colon_content = colon_content[len(existing_whitespace_prefix):]

                            token.value = colon_content

            final_lines_index += 1

            process_content = True
            break

    if not process_content:
      final_lines_index += 1

########################################################################


def _FormatFinalLines(final_lines, verify):
  """Compose the final output from the finalized lines."""
  formatted_code = []
  for line in final_lines:
    formatted_line = []
    for tok in line.tokens:
      if not tok.is_pseudo:
        formatted_line.append(tok.formatted_whitespace_prefix)
        formatted_line.append(tok.value)
      elif (not tok.next_token.whitespace_prefix.startswith('\n') and
            not tok.next_token.whitespace_prefix.startswith(' ')):
        if (tok.previous_token.value == ':' or
            tok.next_token.value not in ',}])'):
          formatted_line.append(' ')

    formatted_code.append(''.join(formatted_line))
    if verify:
      verifier.VerifyCode(formatted_code[-1])

  return ''.join(formatted_code) + '\n'


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

  def __repr__(self):  # pragma: no cover
    return 'StateNode(state=[\n{0}\n], newline={1})'.format(
        self.state, self.newline)


# A tuple of (penalty, count) that is used to prioritize the BFS. In case of
# equal penalties, we prefer states that were inserted first. During state
# generation, we make sure that we insert states first that break the line as
# late as possible.
_OrderedPenalty = collections.namedtuple('OrderedPenalty', ['penalty', 'count'])

# An item in the prioritized BFS search queue. The 'StateNode's 'state' has
# the given '_OrderedPenalty'.
_QueueItem = collections.namedtuple('QueueItem',
                                    ['ordered_penalty', 'state_node'])


def _AnalyzeSolutionSpace(initial_state):
  """Analyze the entire solution space starting from initial_state.

  This implements a variant of Dijkstra's algorithm on the graph that spans
  the solution space (LineStates are the nodes). The algorithm tries to find
  the shortest path (the one with the lowest penalty) from 'initial_state' to
  the state where all tokens are placed.

  Arguments:
    initial_state: (format_decision_state.FormatDecisionState) The initial state
      to start the search from.

  Returns:
    True if a formatting solution was found. False otherwise.
  """
  count = 0
  seen = set()
  p_queue = []

  # Insert start element.
  node = _StateNode(initial_state, False, None)
  heapq.heappush(p_queue, _QueueItem(_OrderedPenalty(0, count), node))

  count += 1
  while p_queue:
    item = p_queue[0]
    penalty = item.ordered_penalty.penalty
    node = item.state_node
    if not node.state.next_token:
      break
    heapq.heappop(p_queue)

    if count > 10000:
      node.state.ignore_stack_for_comparison = True

    # Unconditionally add the state and check if it was present to avoid having
    # to hash it twice in the common case (state hashing is expensive).
    before_seen_count = len(seen)
    seen.add(node.state)
    # If seen didn't change size, the state was already present.
    if before_seen_count == len(seen):
      continue

    # FIXME(morbo): Add a 'decision' element?

    count = _AddNextStateToQueue(penalty, node, False, count, p_queue)
    count = _AddNextStateToQueue(penalty, node, True, count, p_queue)

  if not p_queue:
    # We weren't able to find a solution. Do nothing.
    return False

  _ReconstructPath(initial_state, heapq.heappop(p_queue).state_node)
  return True


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
  must_split = previous_node.state.MustSplit()
  if newline and not previous_node.state.CanSplit(must_split):
    # Don't add a newline if the token cannot be split.
    return count
  if not newline and must_split:
    # Don't add a token we must split but where we aren't splitting.
    return count

  node = _StateNode(previous_node.state, newline, previous_node)
  penalty += node.state.AddTokenToState(
      newline=newline, dry_run=True, must_split=must_split)
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


NESTED_DEPTH = []


def _FormatFirstToken(first_token, indent_depth, prev_line, final_lines):
  """Format the first token in the logical line.

  Add a newline and the required indent before the first token of the logical
  line.

  Arguments:
    first_token: (format_token.FormatToken) The first token in the logical line.
    indent_depth: (int) The line's indentation depth.
    prev_line: (list of logical_line.LogicalLine) The logical line previous to
      this line.
    final_lines: (list of logical_line.LogicalLine) The logical lines that have
      already been processed.
  """
  global NESTED_DEPTH
  while NESTED_DEPTH and NESTED_DEPTH[-1] > indent_depth:
    NESTED_DEPTH.pop()

  first_nested = False
  if _IsClassOrDef(first_token):
    if not NESTED_DEPTH:
      NESTED_DEPTH = [indent_depth]
    elif NESTED_DEPTH[-1] < indent_depth:
      first_nested = True
      NESTED_DEPTH.append(indent_depth)

  first_token.AddWhitespacePrefix(
      _CalculateNumberOfNewlines(first_token, indent_depth, prev_line,
                                 final_lines, first_nested),
      indent_level=indent_depth)


NO_BLANK_LINES = 1
ONE_BLANK_LINE = 2
TWO_BLANK_LINES = 3


def _IsClassOrDef(tok):
  if tok.value in {'class', 'def', '@'}:
    return True
  return (tok.next_token and tok.value == 'async' and
          tok.next_token.value == 'def')


def _CalculateNumberOfNewlines(first_token, indent_depth, prev_line,
                               final_lines, first_nested):
  """Calculate the number of newlines we need to add.

  Arguments:
    first_token: (format_token.FormatToken) The first token in the logical
      line.
    indent_depth: (int) The line's indentation depth.
    prev_line: (list of logical_line.LogicalLine) The logical line previous to
      this line.
    final_lines: (list of logical_line.LogicalLine) The logical lines that have
      already been processed.
    first_nested: (boolean) Whether this is the first nested class or function.

  Returns:
    The number of newlines needed before the first token.
  """
  # TODO(morbo): Special handling for imports.
  # TODO(morbo): Create a knob that can tune these.
  if prev_line is None:
    # The first line in the file. Don't add blank lines.
    # FIXME(morbo): Is this correct?
    if first_token.newlines is not None:
      first_token.newlines = None
    return 0

  if first_token.is_docstring:
    if (prev_line.first.value == 'class' and
        style.Get('BLANK_LINE_BEFORE_CLASS_DOCSTRING')):
      # Enforce a blank line before a class's docstring.
      return ONE_BLANK_LINE
    elif (prev_line.first.value.startswith('#') and
          style.Get('BLANK_LINE_BEFORE_MODULE_DOCSTRING')):
      # Enforce a blank line before a module's docstring.
      return ONE_BLANK_LINE
    # The docstring shouldn't have a newline before it.
    return NO_BLANK_LINES

  if first_token.is_name and not indent_depth:
    if prev_line.first.value in {'from', 'import'}:
      # Support custom number of blank lines between top-level imports and
      # variable definitions.
      return 1 + style.Get(
          'BLANK_LINES_BETWEEN_TOP_LEVEL_IMPORTS_AND_VARIABLES')

  prev_last_token = prev_line.last
  if prev_last_token.is_docstring:
    if (not indent_depth and first_token.value in {'class', 'def', 'async'}):
      # Separate a class or function from the module-level docstring with
      # appropriate number of blank lines.
      return 1 + style.Get('BLANK_LINES_AROUND_TOP_LEVEL_DEFINITION')
    if (first_nested and
        not style.Get('BLANK_LINE_BEFORE_NESTED_CLASS_OR_DEF') and
        _IsClassOrDef(first_token)):
      first_token.newlines = None
      return NO_BLANK_LINES
    if _NoBlankLinesBeforeCurrentToken(prev_last_token.value, first_token,
                                       prev_last_token):
      return NO_BLANK_LINES
    else:
      return ONE_BLANK_LINE

  if _IsClassOrDef(first_token):
    # TODO(morbo): This can go once the blank line calculator is more
    # sophisticated.
    if not indent_depth:
      # This is a top-level class or function.
      is_inline_comment = prev_last_token.whitespace_prefix.count('\n') == 0
      if (not prev_line.disable and prev_last_token.is_comment and
          not is_inline_comment):
        # This token follows a non-inline comment.
        if _NoBlankLinesBeforeCurrentToken(prev_last_token.value, first_token,
                                           prev_last_token):
          # Assume that the comment is "attached" to the current line.
          # Therefore, we want two blank lines before the comment.
          index = len(final_lines) - 1
          while index > 0:
            if not final_lines[index - 1].is_comment:
              break
            index -= 1
          if final_lines[index - 1].first.value == '@':
            final_lines[index].first.AdjustNewlinesBefore(NO_BLANK_LINES)
          else:
            prev_last_token.AdjustNewlinesBefore(
                1 + style.Get('BLANK_LINES_AROUND_TOP_LEVEL_DEFINITION'))
          if first_token.newlines is not None:
            first_token.newlines = None
          return NO_BLANK_LINES
    elif _IsClassOrDef(prev_line.first):
      if first_nested and not style.Get(
          'BLANK_LINE_BEFORE_NESTED_CLASS_OR_DEF'):
        first_token.newlines = None
        return NO_BLANK_LINES

  # Calculate how many newlines were between the original lines. We want to
  # retain that formatting if it doesn't violate one of the style guide rules.
  if first_token.is_comment:
    first_token_lineno = first_token.lineno - first_token.value.count('\n')
  else:
    first_token_lineno = first_token.lineno

  prev_last_token_lineno = prev_last_token.lineno
  if prev_last_token.is_multiline_string:
    prev_last_token_lineno += prev_last_token.value.count('\n')

  if first_token_lineno - prev_last_token_lineno > 1:
    return ONE_BLANK_LINE

  return NO_BLANK_LINES


def _SingleOrMergedLines(lines):
  """Generate the lines we want to format.

  Arguments:
    lines: (list of logical_line.LogicalLine) Lines we want to format.

  Yields:
    Either a single line, if the current line cannot be merged with the
    succeeding line, or the next two lines merged into one line.
  """
  index = 0
  last_was_merged = False
  while index < len(lines):
    if lines[index].disable:
      line = lines[index]
      index += 1
      while index < len(lines):
        column = line.last.column + 2
        if lines[index].lineno != line.lineno:
          break
        if line.last.value != ':':
          leaf = pytree.Leaf(
              type=token.SEMI, value=';', context=('', (line.lineno, column)))
          line.AppendToken(
              format_token.FormatToken(leaf, pytree_utils.NodeName(leaf)))
        for tok in lines[index].tokens:
          line.AppendToken(tok)
        index += 1
      yield line
    elif line_joiner.CanMergeMultipleLines(lines[index:], last_was_merged):
      # TODO(morbo): This splice is potentially very slow. Come up with a more
      # performance-friendly way of determining if two lines can be merged.
      next_line = lines[index + 1]
      for tok in next_line.tokens:
        lines[index].AppendToken(tok)
      if (len(next_line.tokens) == 1 and next_line.first.is_multiline_string):
        # This may be a multiline shebang. In that case, we want to retain the
        # formatting. Otherwise, it could mess up the shell script's syntax.
        lines[index].disable = True
      yield lines[index]
      index += 2
      last_was_merged = True
    else:
      yield lines[index]
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
    cur_token: (format_token.FormatToken) The current token in the logical line.
    prev_token: (format_token.FormatToken) The previous token in the logical
      line.

  Returns:
    True if there is no blank line before the current token.
  """
  cur_token_lineno = cur_token.lineno
  if cur_token.is_comment:
    cur_token_lineno -= cur_token.value.count('\n')
  num_newlines = text.count('\n') if not prev_token.is_comment else 0
  return prev_token.lineno + num_newlines == cur_token_lineno - 1
