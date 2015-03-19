====
YAPF
====

.. image:: https://travis-ci.org/google/yapf.svg?branch=master
    :target: https://travis-ci.org/google/yapf
    :alt: Build status

Introduction
============

Most of the current formatters for Python -- e.g., autopep8, and pep8ify -- are
made to remove lint errors from code. This has some obvious limitations. For
instance, code that conforms to the PEP 8 guidelines may not be reformatted.
But it doesn't mean that the code looks good.

YAPF takes a different approach. It's based off of 'clang-format', developed by
Daniel Jasper. In essence, the algorithm takes the code and reformats it to the
best formatting that conforms to the style guide, even if the original code
didn't violate the style guide.

The ultimate goal is that the code YAPF produces is as good as the code that a
programmer would write if they were following the style guide.

.. contents::

Installation
============

From source directory::

    $ sudo python ./setup.py install


Usage
=====

Options::

    usage: __main__.py [-h] [-d | -i] [-l START-END | -r] ...

    Formatter for Python code.

    positional arguments:
      files

    optional arguments:
      -h, --help            show this help message and exit
      -d, --diff            print the diff for the fixed source
      -i, --in-place        make changes to files in place
      -l START-END, --lines START-END
                            range of lines to reformat, one-based
      -r, --recursive       run recursively over directories


Why Not Improve Existing Tools?
===============================

We wanted to use clang-format's reformatting algorithm. It's very powerful and
designed to come up with the best formatting possible. Existing tools were
created with different goals in mind, and would require extensive modifications
to convert to using clang-format's algorithm.


Can I Use YAPF In My Program?
=============================

Please do! YAPF was designed to be used as a library as well as a command line
tool. This means that a tool or IDE plugin is free to use YAPF.


Gory Details
============

Algorithm Design
----------------

The main data structure in YAPF is the UnwrappedLine object. It holds a list of
FormatTokens, that we would want to place on a single line if there were no
column limit. An exception being a comment in the middle of an expression
statement will force the line to be formatted on more than one line. The
formatter works on one UnwrappedLine object at a time.

An UnwrappedLine typically won't affect the formatting of lines before or after
it. There is a part of the algorithm that may join two or more UnwrappedLines
into one line. For instance, an if-then statement with a short body can be
placed on a single line::

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
FormattingDecisionState object) is the state of the line at that token given the
decision to split before the token or not. Note: the FormatDecisionState objects
are copied by value so each node in the graph is unique and a change in one
doesn't affect other nodes.

Heuristics are used to determine the costs of splitting or not splitting.
Because a node holds the state of the tree up to a token's insertion, it can
easily determine if a splitting decision will violate one of the style
requirements. For instance, the heuristic is able to apply an extra penalty to
the edge when not splitting between the previous token and the one being added.

There are some instances where we will never want to split the line, because
doing so will always be detrimental (i.e., it will require a backslash-newline,
which is very rarely desirable). For line (1), we will never want to split the
first three tokens: 'def', 'xxxxxxxxxxx', and '('. Nor will we want to split
between the ')' and the ':' at the end. These regions are said to be
"unbreakable." This is reflected in the tree by there not being a 'split'
decision (left hand branch) within the unbreakable region.

Now that we have the tree, we determine what the "best" formatting is by finding
the path through the tree with the lowest cost.

And that's it!
