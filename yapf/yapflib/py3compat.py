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
"""Utilities for Python2 / Python3 compatibility."""

import codecs
import io
import sys

PY38 = sys.version_info >= (3, 8)
PY310 = sys.version_info >= (3, 10)


def raw_input():
  wrapper = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
  return wrapper.buffer.raw.readall().decode('utf-8')


def removeBOM(source):
  """Remove any Byte-order-Mark bytes from the beginning of a file."""
  bom = codecs.BOM_UTF8
  bom = bom.decode('utf-8')
  if source.startswith(bom):
    return source[len(bom):]
  return source
