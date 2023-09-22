# How to Contribute

Want to contribute? Great! First, read this page (including the small print at
the end).

## Before you contribute

Before we can use your code, you must sign the [Google Individual Contributor
License Agreement](https://developers.google.com/open-source/cla/individual?csw=1)
(CLA), which you can do online. The CLA is necessary mainly because you own the
copyright to your changes, even after your contribution becomes part of our
codebase, so we need your permission to use and distribute your code. We also
need to be sure of various other things—for instance that you'll tell us if you
know that your code infringes on other people's patents. You don't have to sign
the CLA until after you've submitted your code for review and a member has
approved it, but you must do it before we can put your code into our codebase.
Before you start working on a larger contribution, you should get in touch with
us first through the issue tracker with your idea so that we can help out and
possibly guide you. Coordinating up front makes it much easier to avoid
frustration later on.

## Code reviews

All submissions, including submissions by project members, require review. We
use Github pull requests for this purpose.

## YAPF coding style

YAPF follows the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
with two exceptions:

- 2 spaces for indentation rather than 4.
- CamelCase for function and method names rather than `snake_case`.

The rationale for this is that YAPF was initially developed at Google where
these two exceptions are still part of the internal Python style guide.

## Getting started
YAPF supports using tox 3 for creating a local dev environment, testing, and
building redistributables. See [HACKING.md](HACKING.md) for more info.

```bash
$ pipx run --spec='tox<4' tox --devenv .venv
```

## Small print

Contributions made by corporations are covered by a different agreement than
the one above, the Software Grant and Corporate Contributor License Agreement.
