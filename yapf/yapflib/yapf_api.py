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
"""Entry points for YAPF.

The main APIs that YAPF exposes to drive the reformatting.

  FormatFile(): reformat a file.
  FormatCode(): reformat a string of code.

These APIs have some common arguments:

  style_config: (string) Either a style name or a path to a file that contains
    formatting style settings. If None is specified, use the default style
    as set in style.DEFAULT_STYLE_FACTORY
  lines: (list of tuples of integers) A list of tuples of lines, [start, end],
    that we want to format. The lines are 1-based indexed. It can be used by
    third-party code (e.g., IDEs) when reformatting a snippet of code rather
    than a whole file.
  print_diff: (bool) Instead of returning the reformatted source, return a
    diff that turns the formatted source into reformatter source.
"""

import difflib
import io
import logging
import re

from yapf.yapflib import blank_line_calculator
from yapf.yapflib import comment_splicer
from yapf.yapflib import pytree_unwrapper
from yapf.yapflib import pytree_utils
from yapf.yapflib import reformatter
from yapf.yapflib import split_penalty
from yapf.yapflib import style
from yapf.yapflib import subtype_assigner


def FormatFile(filename, style_config=None, lines=None, print_diff=False):
  """Format a single Python file and return the formatted code.

  Arguments:
    filename: (unicode) The file to reformat.
    style_config, lines, print_diff: see comment at the top of this module.

  Returns:
    The reformatted code or None if the file doesn't exist.
  """
  original_source = ReadFile(filename, logging.warning)
  if original_source is None:
    return None

  return FormatCode(original_source,
                    style_config=style_config,
                    filename=filename,
                    lines=lines,
                    print_diff=print_diff)


def FormatCode(unformatted_source,
               filename='<unknown>',
               style_config=None,
               lines=None,
               print_diff=False):
  """Format a string of Python code.

  This provides an alternative entry point to YAPF.

  Arguments:
    unformatted_source: (unicode) The code to format.
    filename: (unicode) The name of the file being reformatted.
    style_config, lines, print_diff: see comment at the top of this module.

  Returns:
    The code reformatted to conform to the desired formatting style.
  """
  style.SetGlobalStyle(style.CreateStyleFromConfig(style_config))
  tree = pytree_utils.ParseCodeToTree(unformatted_source.rstrip() + '\n')

  # Run passes on the tree, modifying it in place.
  comment_splicer.SpliceComments(tree)
  subtype_assigner.AssignSubtypes(tree)
  split_penalty.ComputeSplitPenalties(tree)
  blank_line_calculator.CalculateBlankLines(tree)

  uwlines = pytree_unwrapper.UnwrapPyTree(tree)
  if not uwlines:
    return ''
  for uwl in uwlines:
    uwl.CalculateFormattingInformation()

  if lines is not None:
    reformatted_source = _FormatLineSnippets(unformatted_source, uwlines, lines)
  else:
    lines = _LinesToFormat(uwlines)
    if lines:
      reformatted_source = _FormatLineSnippets(unformatted_source, uwlines,
                                               lines)
    else:
      reformatted_source = reformatter.Reformat(uwlines)

  if unformatted_source == reformatted_source:
    return '' if print_diff else reformatted_source

  code_diff = _GetUnifiedDiff(unformatted_source, reformatted_source,
                              filename=filename)

  if print_diff:
    return code_diff

  return reformatted_source


def ReadFile(filename, logger=None):
  """Read the contents of the file.

  An optional logger can be specified to emit messages to your favorite logging
  stream. If specified, then no exception is raised.

  Arguments:
    filename: (unicode) The name of the file.
    logger: (function) A function or lambda that takes a string and emits it.

  Returns:
    The contents of filename.

  Raises:
    IOError: raised during an error if a logger is not specified.
  """
  try:
    with io.open(filename, mode='r', newline='') as fd:
      source = fd.read()
    return source
  except IOError as err:
    if logger:
      logger(err)
    else:
      raise


DISABLE_PATTERN = r'^#+ +yapf: *disable$'
ENABLE_PATTERN = r'^#+ +yapf: *enable$'


def _LinesToFormat(uwlines):
  """Skip sections of code that we shouldn't reformat."""
  start = 1
  lines = []
  for uwline in uwlines:
    if uwline.is_comment:
      if re.search(DISABLE_PATTERN, uwline.first.value.strip(), re.IGNORECASE):
        lines.append((start, uwline.lineno))
      elif re.search(ENABLE_PATTERN, uwline.first.value.strip(), re.IGNORECASE):
        start = uwline.lineno
    elif re.search(DISABLE_PATTERN, uwline.last.value.strip(), re.IGNORECASE):
      # Disable only one line.
      if uwline.lineno != start:
        lines.append((start, uwline.lineno - 1))
      start = uwline.last.lineno + 1

  if start != 1 and start <= uwlines[-1].last.lineno + 1:
    lines.append((start, uwlines[-1].last.lineno))
  return lines


def _FormatLineSnippets(unformatted_source, uwlines, lines):
  """Format a string of Python code.

  This provides an alternative entry point to YAPF.

  Arguments:
    unformatted_source: (unicode) The code to format.
    uwlines: (list of UnwrappedLine) The unwrapped lines.
    lines: (list of tuples of integers) A list of lines that we want to format.
      The lines are 1-indexed.

  Returns:
    The code reformatted to conform to the desired formatting style.
  """
  # First we reformat only those lines that we want to reformat.
  index = 0
  reformatted_sources = dict()
  for start, end in sorted(lines):
    snippet = []
    while index < len(uwlines):
      if start <= uwlines[index].lineno or start < uwlines[index].last.lineno:
        while index < len(uwlines):
          if end < uwlines[index].lineno:
            break
          snippet.append(uwlines[index])
          index += 1
        break
      index += 1
    # Make sure to re-add preceding blank lines to the code snippet.
    blank_lines = ''
    if snippet:
      blank_lines = '\n' * (snippet[0].lineno - start)
      if snippet[0].is_comment:
        if snippet[0].first.value.count('\n') == len(blank_lines):
          blank_lines = ''
    reformatted_sources[(start, end)] = (
        blank_lines + reformatter.Reformat(snippet).rstrip()
    )

  # Next we reconstruct the finalized lines inserting the reformatted lines at
  # the appropriate places.
  prev_end = 0
  finalized_lines = []
  unformatted_lines = unformatted_source.splitlines()
  for key in sorted(reformatted_sources):
    start, end = key
    finalized_lines.extend(unformatted_lines[prev_end:start - 1])
    finalized_lines.append(reformatted_sources[key])
    prev_end = end

  # If there are any remaining lines, place them at the end.
  if prev_end < len(unformatted_lines):
    finalized_lines.extend(unformatted_lines[prev_end:])

  # Construct the reformatted sources.
  return '\n'.join(finalized_lines).rstrip() + '\n'


def _GetUnifiedDiff(before, after, filename='code'):
  """Get a unified diff of the changes.

  Arguments:
    before: (unicode) The original source code.
    after: (unicode) The reformatted source code.
    filename: (unicode) The code's filename.

  Returns:
    The unified diff text.
  """
  before = before.splitlines()
  after = after.splitlines()
  return '\n'.join(difflib.unified_diff(before, after, filename, filename,
                                        '(original)', '(reformatted)',
                                        lineterm='')) + '\n'
