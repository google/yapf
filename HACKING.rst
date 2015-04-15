Releasing a new version
-----------------------

* Run tests: python setup.py test
  [don't forget to run with Python 2.7 and 3.4]

* Bump version in yapf/__init__.py

* Build source distribution: python setup.py sdist

* Check it looks OK, install it onto a virtualenv, run tests, run yapf as a tool

* Push to PyPI: python setup.py sdist upload

* Test in a clean virtualenv that 'pip install yapf' works with the new version

* Commit the version bump; add tag with git tag v<VERSION_NUM>; git push --tags

TODO: discuss how to use tox to make virtualenv testing easier.
