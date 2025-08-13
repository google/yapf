## Running YAPF on itself

- To run YAPF on all of YAPF:

```bash
$ pipx run --spec=${PWD} --no-cache yapf -m -i -r yapf/ yapftests/ third_party/
```

- To run YAPF on just the files changed in the current git branch:

```bash
$ pipx run --spec=${PWD} --no-cache yapf -m -i $(git diff --name-only @{upstream})
```

## Testing and building redistributables locally

YAPF uses tox 3 to test against multiple python versions and to build redistributables.

Tox will opportunistically use pyenv environments when available.
To configure pyenv run the following in bash:

```bash
$ xargs -t -n1 pyenv install  < .python-version
```

Test against all supported Python versions that are currently installed:
```bash
$ pipx run --spec='tox<4' tox
```

Build and test the sdist and wheel against your default Python environment. The redistributables will be in the `dist` directory.
```bash
$ pipx run --spec='tox<4' tox -e bdist_wheel -e sdist
```

## Releasing a new version

1. Install all expected pyenv environements
    ```bash
    $ xargs -t -n1 pyenv install  < .python-version
    ```

1. Run tests against Python 3.7 - 3.11 with
    ```bash
    $ pipx run --spec='tox<4' tox
    ```

1. Bump version in `yapf/_version.py`.

1. Build and test redistributables

    ```bash
    $ pipx run --spec='tox<4' tox -e bdist_wheel -e sdist
    ```

1. Check that it looks OK.
   1. Install it onto a virtualenv,
   1. run tests, and
   1. run yapf as a tool.

1. Push to PyPI:

    ```bash
    $ pipx run twine upload dist/*
    ```

1. Test in a clean virtualenv that 'pip install yapf' works with the new
  version.

1. Commit the version bump and add tag with:

    ```bash
    $ git tag v$(VERSION_NUM)
    $ git push --tags
    ```
