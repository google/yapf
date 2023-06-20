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

from setuptools import Command
from setuptools import find_packages
from setuptools import setup


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


with codecs.open('README.rst', 'r', 'utf-8') as fd:
  setup(
      name='yapf',
      version='0.40.1',
      description='A formatter for Python code.',
      url='https://github.com/google/yapf',
      long_description=fd.read(),
      license='Apache License, Version 2.0',
      author='Google Inc.',
      maintainer='Bill Wendling',
      maintainer_email='morbo@google.com',
      options={'bdist_wheel': {
          'python_tag': 'py3'
      }},
      packages=find_packages(where='.', include=['yapf*', 'yapftests*']) +
      find_packages(where='third_party'),
      package_dir={'yapf_third_party': 'third_party/yapf_third_party'},
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
          'Programming Language :: Python :: 3 :: Only',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Programming Language :: Python :: 3.11',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Software Development :: Quality Assurance',
      ],
      entry_points={
          'console_scripts': [
              'yapf = yapf:run_main',
              'yapf-diff = yapf_third_party.yapf_diff.yapf_diff:main',
          ],
      },
      cmdclass={
          'test': RunTests,
      },
      package_data={
          'yapf_third_party': [
              'yapf_diff/LICENSE',
              '_ylib2to3/Grammar.txt',
              '_ylib2to3/PatternGrammar.txt',
              '_ylib2to3/LICENSE',
          ]
      },
      include_package_data=True,
      python_requires='>=3.7',
      install_requires=[
          'importlib-metadata>=6.6.0',
          'platformdirs>=3.5.1',
          'tomli>=2.0.1',
      ],
  )
