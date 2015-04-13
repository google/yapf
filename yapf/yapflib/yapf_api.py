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
  style_opts: (dict) Dictionary of style overrides.
  lines: (list of tuples of integers) A list of tuples of lines, [start, end],
    that we want to format. The lines are 1-based indexed. It can be used by
    third-party code (e.g., IDEs) when reformatting a snippet of code rather
    than a whole file.
  print_diff: (bool) Instead of returning the reformatted source, return a
    diff that turns the formatted source into reformatter source.
  verify: (bool) True if reformatted code should be verified for syntax.
"""

import difflib
import io
import logging
import re
import sys

from yapf.yapflib import blank_line_calculator
from yapf.yapflib import comment_splicer
from yapf.yapflib import continuation_splicer
from yapf.yapflib import pytree_unwrapper
from yapf.yapflib import pytree_utils
from yapf.yapflib import reformatter
from yapf.yapflib import split_penalty
from yapf.yapflib import style
from yapf.yapflib import subtype_assigner


def FormatFile(filename,
               style_config=None,
               style_opts=None,
               lines=None,
               print_diff=False,
               verify=True):
  """Format a single Python file and return the formatted code.

  Arguments:
    filename: (unicode) The file to reformat.
    remaining arguments: see comment at the top of this module.

  Returns:
    The reformatted code or None if the file doesn't exist.
  """
  _CheckPythonVersion()
  original_source = ReadFile(filename, logging.warning)
  if original_source is None:
    return None

  return FormatCode(original_source,
                    style_config=style_config,
                    style_opts=style_opts,
                    filename=filename,
                    lines=lines,
                    print_diff=print_diff,
                    verify=verify)


def FormatCode(unformatted_source,
               filename='<unknown>',
               style_config=None,
               style_opts=None,
               lines=None,
               print_diff=False,
               verify=True):
  """Format a string of Python code.

  This provides an alternative entry point to YAPF.

  Arguments:
    unformatted_source: (unicode) The code to format.
    filename: (unicode) The name of the file being reformatted.
    remaining arguments: see comment at the top of this module.

  Returns:
    The code reformatted to conform to the desired formatting style.
  """
  _CheckPythonVersion()
  style.SetGlobalStyle(style.CreateStyleFromConfig(style_config, style_opts))
  if not unformatted_source.endswith('\n'):
    unformatted_source += '\n'
  tree = pytree_utils.ParseCodeToTree(unformatted_source)

  # Run passes on the tree, modifying it in place.
  comment_splicer.SpliceComments(tree)
  continuation_splicer.SpliceContinuations(tree)
  subtype_assigner.AssignSubtypes(tree)
  split_penalty.ComputeSplitPenalties(tree)
  blank_line_calculator.CalculateBlankLines(tree)

  uwlines = pytree_unwrapper.UnwrapPyTree(tree)
  if not uwlines:
    return ''
  for uwl in uwlines:
    uwl.CalculateFormattingInformation()

  _MarkLinesToFormat(uwlines, lines)
  reformatted_source = reformatter.Reformat(uwlines, verify)

  if unformatted_source == reformatted_source:
    return '' if print_diff else reformatted_source

  code_diff = _GetUnifiedDiff(unformatted_source, reformatted_source,
                              filename=filename)

  if print_diff:
    return code_diff

  return reformatted_source


def _CheckPythonVersion():
  errmsg = 'yapf is only supported for Python 2.7 or 3.4+'
  if sys.version_info[0] == 2:
    if sys.version_info[1] < 7:
      raise RuntimeError(errmsg)
  elif sys.version_info[0] == 3:
    if sys.version_info[1] < 4:
      raise RuntimeError(errmsg)


def ReadFile(filename, logger=None):
  """Read the contents of the file.

  An optional logger can be specified to emit messages to your favorite logging
  stream. If specified, then no exception is raised. This is external so that it
  can be used by third-party applications.

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


def _MarkLinesToFormat(uwlines, lines):
  """Skip sections of code that we shouldn't reformat."""
  if lines:
    for uwline in uwlines:
      uwline.disable = True

    for start, end in sorted(lines):
      for uwline in uwlines:
        if uwline.lineno > end:
          break
        if uwline.lineno >= start:
          uwline.disable = False
    return

  index = 0
  while index < len(uwlines):
    uwline = uwlines[index]
    if uwline.is_comment:
      if re.search(DISABLE_PATTERN, uwline.first.value.strip(), re.IGNORECASE):
        while index < len(uwlines):
          uwline = uwlines[index]
          uwline.disable = True
          if (uwline.is_comment and
              re.search(ENABLE_PATTERN, uwline.first.value.strip(),
                        re.IGNORECASE)):
            break
          index += 1
    elif re.search(DISABLE_PATTERN, uwline.last.value.strip(), re.IGNORECASE):
      uwline.disable = True
    index += 1


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
