====
YAPF
====

.. image:: https://badge.fury.io/py/yapf.svg
    :target: http://badge.fury.io/py/yapf
    :alt: PyPI version

.. image:: https://travis-ci.org/google/yapf.svg?branch=master
    :target: https://travis-ci.org/google/yapf
    :alt: Build status

.. image:: https://coveralls.io/repos/google/yapf/badge.svg?branch=master
    :target: https://coveralls.io/r/google/yapf?branch=master
    :alt: Coverage status

Introduction
============

Most of the current formatters for Python --- e.g., autopep8, and pep8ify ---
are made to remove lint errors from code. This has some obvious limitations.
For instance, code that conforms to the PEP 8 guidelines may not be
reformatted.  But it doesn't mean that the code looks good.

YAPF takes a different approach. It's based off of 'clang-format', developed by
Daniel Jasper. In essence, the algorithm takes the code and reformats it to the
best formatting that conforms to the style guide, even if the original code
didn't violate the style guide. The idea is also similar to the 'gofmt' tool for
the Go programming language: end all holy wars about formatting - if the whole
code base of a project is simply piped through YAPF whenever modifications are
made, the style remains consistent throughout the project and there's no point
arguing about style in every code review.

The ultimate goal is that the code YAPF produces is as good as the code that a
programmer would write if they were following the style guide. It takes away
some of the drudgery of maintaining your code.

.. footer::

    YAPF is not an official Google product (experimental or otherwise), it is
    just code that happens to be owned by Google.

.. contents::

Installation
============

To install YAPF from PyPI::

    $ pip install yapf

YAPF is still considered in "alpha" stage, and the released version may change
often; therefore, the best way to keep up-to-date with the latest development
is to clone this repository.

Note that if you intend to use YAPF as a command-line tool rather than as a
library, installation is not necessary. YAPF supports being run as a directory
by the Python interpreter. If you cloned/unzipped YAPF into ``DIR``, it's
possible to run::

    $ PYTHONPATH=DIR python DIR/yapf [options] ...

Python versions
===============

YAPF supports Python 2.7 and 3.4.1+.

YAPF requires the code it formats to be valid Python for the version YAPF itself
runs under. Therefore, if you format Python 3 code with YAPF, run YAPF itself
under Python 3 (and similarly for Python 2).

Usage
=====

Options::

    usage: yapf [-h] [--style STYLE] [-d | -i] [-l START-END | -r] ...

    Formatter for Python code.

    positional arguments:
      files

    optional arguments:
      -h, --help            show this help message and exit
      --style STYLE         specify formatting style: either a style name (for
                            example "pep8" or "google"), or the name of a file
                            with style settings. pep8 is the default.
      -d, --diff            print the diff for the fixed source
      -i, --in-place        make changes to files in place
      -l START-END, --lines START-END
                            range of lines to reformat, one-based
      -r, --recursive       run recursively over directories

Formatting style
================

The formatting style used by YAPF is configurable and there are many "knobs"
that can be used to tune how YAPF does formatting. See the ``style.py`` module
for the full list.

To control the style, run YAPF with the ``--style`` argument. It accepts one of
the predefined styles (e.g., ``pep8`` or ``google``), a path to a configuration
file that specifies the desired style, or a dictionary of key/value pairs.

The config file is a simple listing of (case-insensitive) ``key = value`` pairs
with a ``[style]`` heading. For example::

    [style]
    based_on_style = pep8
    spaces_before_comment = 4
    split_before_logical_operator = true

The ``based_on_style`` setting determines which of the predefined styles this
custom style is based on (think of it like subclassing).

It's also possible to do the same on the command line with a dictionary. For
example::

    --style='{based_on_style: google, indent_width: 4}'

This will take the ``google`` base style and modify it to have four space
indentations.

Example
=======

An example of the type of formatting that YAPF can do, it will take this ugly
code:

.. code-block:: python

    x = {  'a':37,'b':42,

    'c':927}

    y = 'hello ''world'
    z = 'hello '+'world'
    a = 'hello {}'.format('world')
    class foo  (     object  ):
      def f    (self   ):
        return       37*-+2
      def g(self, x,y=42):
          return y
    def f  (   a ) :
      return      37+-+a[42-x :  y**3]

and reformat it into:

.. code-block:: python

    x = {'a': 37, 'b': 42, 'c': 927}

    y = 'hello ' 'world'
    z = 'hello ' + 'world'
    a = 'hello {}'.format('world')


    class foo(object):
        def f(self):
            return 37 * -+2

        def g(self, x, y=42):
            return y


    def f(a):
        return 37 + -+a[42 - x:y ** 3]

(Potentially) Frequently Asked Questions
========================================

Why does YAPF destroy my awesome formatting?
--------------------------------------------

YAPF tries very hard to get the formatting correct. But for some code, it won't
be as good as hand-formatting. In particular, large data literals may become
horribly disfigured under YAPF.

The reason for this is many-fold. But in essence YAPF is simply a tool to help
with development. It will format things to coincide with the style guide, but
that may not equate with readability.

What can be done to alleviate this situation is to indicate regions YAPF should
ignore when reformatting something:

.. code-block:: python

    # yapf: disable
    FOO = {
        # ... some very large, complex data literal.
    }

    BAR = [
        # ... another large data literal.
    ]
    # yapf: enable

You can also disable formatting for a single literal like this:

.. code-block:: python

    BAZ = {
        [1, 2, 3, 4],
        [5, 6, 7, 8],
        [9, 10, 11, 12]
    }  # yapf: disable

Why Not Improve Existing Tools?
-------------------------------

We wanted to use clang-format's reformatting algorithm. It's very powerful and
designed to come up with the best formatting possible. Existing tools were
created with different goals in mind, and would require extensive modifications
to convert to using clang-format's algorithm.

Can I Use YAPF In My Program?
-----------------------------

Please do! YAPF was designed to be used as a library as well as a command line
tool. This means that a tool or IDE plugin is free to use YAPF.

Gory Details
============

Algorithm Design
----------------

The main data structure in YAPF is the ``UnwrappedLine`` object. It holds a list
of ``FormatToken``\s, that we would want to place on a single line if there were
no column limit. An exception being a comment in the middle of an expression
statement will force the line to be formatted on more than one line. The
formatter works on one ``UnwrappedLine`` object at a time.

An ``UnwrappedLine`` typically won't affect the formatting of lines before or
after it. There is a part of the algorithm that may join two or more
``UnwrappedLine``\s into one line. For instance, an if-then statement with a
short body can be placed on a single line:

.. code-block:: python

    if a == 42: continue

YAPF's formatting algorithm creates a weighted tree that acts as the solution
space for the algorithm. Each node in the tree represents the result of a
formatting decision --- i.e., whether to split or not to split before a token.
Each formatting decision has a cost associated with it. Therefore, the cost is
realized on the edge between two nodes. (In reality, the weighted tree doesn't
have separate edge objects, so the cost resides on the nodes themselves.)

For example, take the following Python code snippet. For the sake of this
example, assume that line (1) violates the column limit restriction and needs to
be reformatted.

.. code-block:: python

    def xxxxxxxxxxx(aaaaaaaaaaaa, bbbbbbbbb, cccccccc, dddddddd, eeeeee):  # 1
        pass                                                               # 2

For line (1), the algorithm will build a tree where each node (a
``FormattingDecisionState`` object) is the state of the line at that token given
the decision to split before the token or not. Note: the ``FormatDecisionState``
objects are copied by value so each node in the graph is unique and a change in
one doesn't affect other nodes.

Heuristics are used to determine the costs of splitting or not splitting.
Because a node holds the state of the tree up to a token's insertion, it can
easily determine if a splitting decision will violate one of the style
requirements. For instance, the heuristic is able to apply an extra penalty to
the edge when not splitting between the previous token and the one being added.

There are some instances where we will never want to split the line, because
doing so will always be detrimental (i.e., it will require a backslash-newline,
which is very rarely desirable). For line (1), we will never want to split the
first three tokens: ``def``, ``xxxxxxxxxxx``, and ``(``. Nor will we want to
split between the ``)`` and the ``:`` at the end. These regions are said to be
"unbreakable." This is reflected in the tree by there not being a "split"
decision (left hand branch) within the unbreakable region.

Now that we have the tree, we determine what the "best" formatting is by finding
the path through the tree with the lowest cost.

And that's it!
