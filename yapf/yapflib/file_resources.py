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
"""Interface to file resources.

This module provides functions for interfacing with files: opening, writing, and
querying.
"""

import io
import os
import sys

from yapf.yapflib import py3compat


def GetCommandLineFiles(command_line_file_list, recursive):
  """Return the list of files specified on the command line."""
  return _FindFiles(command_line_file_list, recursive)


def WriteReformattedCode(filename, reformatted_code, in_place):
  """Emit the reformatted code.

  Write the reformatted code into the file, if in_place is True. Otherwise,
  write to stdout.

  Arguments:
    filename: (unicode) The name of the unformatted file.
    reformatted_code: (unicode) The reformatted code.
    in_place: (bool) If True, then write the reformatted code to the file.
  """
  if not reformatted_code.strip():
    return
  if in_place:
    with io.open(filename, mode='w', newline='') as fd:
      fd.write(reformatted_code)
  else:
    sys.stdout.write(py3compat.EncodeForStdout(reformatted_code))


def _FindFiles(filenames, recursive):
  """Find all Python files."""
  python_files = []
  for filename in filenames:
    if os.path.isdir(filename):
      if recursive:
        # TODO(morbo): Look into a version of os.walk that can handle recursion.
        python_files.extend(os.path.join(dirpath, f)
                            for dirpath, _, filelist in os.walk(filename)
                            for f in filelist
                            if IsPythonFile(os.path.join(dirpath, f)))
      else:
        python_files.extend(os.path.join(filename, f)
                            for f in os.listdir(filename)
                            if IsPythonFile(os.path.join(filename, f)))
    elif os.path.isfile(filename) and IsPythonFile(filename):
      python_files.append(filename)

  return python_files


def IsPythonFile(filename):
  """Return True if filename is a Python file."""
  return os.path.splitext(filename)[1] == '.py'
