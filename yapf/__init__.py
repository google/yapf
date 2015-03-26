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
"""YAPF.

YAPF uses the algorithm in clang-format to figure out the "best" formatting for
Python code. It looks at the program as a series of "unwrappable lines" ---
i.e., lines which, if there were no column limit, we would place all tokens on
that line. It then uses a priority queue to figure out what the best formatting
is --- i.e., the formatting with the least penalty.

It differs from tools like autopep8 and pep8ify in that it doesn't just look for
violations of the style guide, but looks at the module as a whole, making
formatting decisions based on what's the best format for each line.

If no filenames are specified, YAPF reads the code from stdin.
"""

import argparse
import logging
import sys

from yapf.yapflib import file_resources
from yapf.yapflib import py3compat
from yapf.yapflib import yapf_api

__version__ = '0.1'


def main(argv):
  """Main program.

  Arguments:
    argv: (Positional arguments) A list of files to reformat.

  Returns:
    0 if there were no errors, non-zero otherwise.
  """
  parser = argparse.ArgumentParser(description='Formatter for Python code.')
  parser.add_argument(
      '--style', action='store', default=None,
      help=('specify formatting style: either a style name (for example "pep8" '
            'or "google"), or the name of a file with style settings'))
  diff_inplace_group = parser.add_mutually_exclusive_group()
  diff_inplace_group.add_argument(
      '-d', '--diff', action='store_true',
      help='print the diff for the fixed source')
  diff_inplace_group.add_argument(
      '-i', '--in-place', action='store_true',
      help='make changes to files in place')

  lines_recursive_group = parser.add_mutually_exclusive_group()
  lines_recursive_group.add_argument(
      '-l', '--lines', metavar='START-END', action='append', default=None,
      help='range of lines to reformat, one-based')
  lines_recursive_group.add_argument(
      '-r', '--recursive', action='store_true',
      help='run recursively over directories')

  parser.add_argument('files', nargs=argparse.REMAINDER)
  args = parser.parse_args()

  if args.lines and len(args.files) > 1:
    parser.error('cannot use -l/--lines with more than one file')

  lines = _GetLines(args.lines) if args.lines is not None else None
  files = file_resources.GetCommandLineFiles(argv[1:], args.recursive)
  if not files:
    # No arguments specified. Read code from stdin.
    if args.in_place or args.diff:
      parser.error('cannot use --in_place or --diff flags when reading '
                   'from stdin')

    original_source = []
    while True:
      try:
        # Use 'raw_input' instead of 'sys.stdin.read', because otherwise the
        # user will need to hit 'Ctrl-D' more than once if they're inputting
        # the program by hand. 'raw_input' throws an EOFError exception if
        # 'Ctrl-D' is pressed, which makes it easy to bail out of this loop.
        original_source.append(py3compat.raw_input())
      except EOFError:
        break
    sys.stdout.write(yapf_api.FormatCode(
        py3compat.unicode('\n'.join(original_source) + '\n'),
        filename='<stdin>',
        style_config=args.style,
        lines=lines))
    return 0

  FormatFiles(files, lines, style_config=args.style, in_place=args.in_place,
              print_diff=args.diff)
  return 0


def FormatFiles(filenames, lines, style_config=None, in_place=False,
                print_diff=False):
  """Format a list of files.

  Arguments:
    filenames: (list of unicode) A list of files to reformat.
    lines: (list of tuples of integers) A list of tuples of lines, [start, end],
      that we want to format. The lines are 1-based indexed. This argument
      overrides the 'args.lines'. It can be used by third-party code (e.g.,
      IDEs) when reformatting a snippet of code.
    style_config: (string) Style name or file path.
    in_place: (bool) Modify the files in place.
    print_diff: (bool) Instead of returning the reformatted source, return a
      diff that turns the formatted source into reformatter source.
  """
  for filename in filenames:
    logging.info('Reformatting %s', filename)
    reformatted_code = yapf_api.FormatFile(
        filename, style_config=style_config, lines=lines, print_diff=print_diff)
    if reformatted_code is not None:
      file_resources.WriteReformattedCode(filename, reformatted_code, in_place)


def _GetLines(line_strings):
  """Parses the start and end lines from a line string like 'start-end'.

  Arguments:
    line_strings: (array of string) A list of strings representing a line
      range like 'start-end'.

  Returns:
    A list of tuples of the start and end line numbers.

  Raises:
    ValueError: If the line string failed to parse or was an invalid line range.
  """
  lines = []
  for line_string in line_strings:
    # The 'list' here is needed by Python 3.
    line = list(map(int, line_string.split('-', 1)))
    if line[0] < 1:
      raise ValueError('invalid start of line range: %r' % line)
    if line[0] > line[1]:
      raise ValueError('end comes before start in line range: %r', line)
    lines.append(tuple(line))
  return lines


if __name__ == '__main__':
  sys.exit(main(sys.argv))
