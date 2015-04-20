import sys
import textwrap
import unittest

from yapf.yapflib import blank_line_calculator
from yapf.yapflib import comment_splicer
from yapf.yapflib import continuation_splicer
from yapf.yapflib import pytree_unwrapper
from yapf.yapflib import pytree_utils
from yapf.yapflib import pytree_visitor
from yapf.yapflib import reformatter
from yapf.yapflib import split_penalty
from yapf.yapflib import subtype_assigner


class TestingNotInParameters(unittest.TestCase):

    def test_notInParams(self):
        code = textwrap.dedent("""\
            def sum(a, sprint):
                return a


            sum("felipe barreto volpone longo nome para quebrar porque anda nao q",
                not True)
        """)
        uwlines = _ParseAndUnwrap(code)
        self.assertEqual(code, reformatter.Reformat(uwlines))


def _ParseAndUnwrap(code, dumptree=False):
  """Produces unwrapped lines from the given code.

  Parses the code into a tree, performs comment splicing and runs the
  unwrapper.

  Arguments:
    code: code to parse as a string
    dumptree: if True, the parsed pytree (after comment splicing) is dumped
              to stderr. Useful for debugging.

  Returns:
    List of unwrapped lines.
  """
  tree = pytree_utils.ParseCodeToTree(code)
  comment_splicer.SpliceComments(tree)
  continuation_splicer.SpliceContinuations(tree)
  subtype_assigner.AssignSubtypes(tree)
  split_penalty.ComputeSplitPenalties(tree)
  blank_line_calculator.CalculateBlankLines(tree)

  if dumptree:
    pytree_visitor.DumpPyTree(tree, target_stream=sys.stderr)

  uwlines = pytree_unwrapper.UnwrapPyTree(tree)
  for uwl in uwlines:
    uwl.CalculateFormattingInformation()

  return uwlines


if __name__ == '__main__':
  unittest.main()
