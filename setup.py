#!/usr/bin/env python
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

import codecs
import sys
import unittest
from configparser import ConfigParser
from pathlib import Path

from setuptools import Command, find_packages, setup


class RunTests(Command):
  user_options = []

  def initialize_options(self):
    pass

  def finalize_options(self):
    pass

  def run(self):
    loader = unittest.TestLoader()
    tests = loader.discover('yapftests', pattern='*_test.py', top_level_dir='.')
    runner = unittest.TextTestRunner()
    results = runner.run(tests)
    sys.exit(0 if results.wasSuccessful() else 1)


PKG_INFO = ConfigParser()
PKG_INFO_FILE = Path(
    sys.modules[__name__].__file__).parent / 'yapf/PKG_INFO.ini'  # type: ignore
PKG_INFO.read(PKG_INFO_FILE)
PKG_INFO = PKG_INFO['PKG_INFO']

with codecs.open('README.rst', 'r', 'utf-8') as fd:
  setup(
      name='yapf',
      version=PKG_INFO['Version'],
      description='A formatter for Python code.',
      url='https://github.com/google/yapf',
      long_description=fd.read(),
      license='Apache License, Version 2.0',
      author=PKG_INFO['Author'],
      maintainer='Bill Wendling',
      maintainer_email='morbo@google.com',
      packages=find_packages('.'),
      project_urls={
          'Source': 'https://github.com/google/yapf',
      },
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: Apache Software License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Programming Language :: Python :: 3.11',
          'Programming Language :: Python :: 3 :: Only',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Software Development :: Quality Assurance',
      ],
      entry_points={
          'console_scripts': [
              'yapf = yapf:run_main',
              'yapf-diff = yapf.third_party.yapf_diff.yapf_diff:main',
          ],
      },
      cmdclass={
          'test': RunTests,
      },
      package_data={
          'yapf': [
              'PKG_INFO.ini',
              'third_party/yapf_diff/LICENSE',
              'third_party/_ylib2to3/Grammar.txt',
              'third_party/_ylib2to3/PatternGrammar.txt',
              'third_party/_ylib2to3/LICENSE',
          ]
      },
      include_package_data=True,
      python_requires='>=3.7',
      install_requires=['tomli>=2.0.1', 'platformdirs>=3.5.1'],
  )
