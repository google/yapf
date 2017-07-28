===========
IDE Plugins
===========

Emacs
=====

The ``Emacs`` plugin is maintained separately.
Installation directions can be found here: https://github.com/paetzke/py-yapf.el

VIM
===

The ``vim`` plugin allows you to reformat a range of code. Place it into the
``.vim/autoload`` directory or use a plugin manager like Plug or Vundle:

.. code-block:: vim
     " Plug
     Plug 'google/yapf', { 'rtp': 'plugins/vim', 'for': 'python' }

     " Vundle
     Plugin 'google/yapf', { 'rtp': 'plugins/vim' }


You can add key bindings in the ``.vimrc`` file:

.. code-block:: vim

    map <C-Y> :call yapf#YAPF()<cr>
    imap <C-Y> <c-o>:call yapf#YAPF()<cr>

Sublime Text
============

The ``Sublime Text`` plugin is also maintained separately.
It is compatible with both Sublime Text 2 and 3.

The plugin can be easily installed by using *Sublime Package Control*.
Check the project page of the plugin for more information:
https://github.com/jason-kane/PyYapf

===================
git Pre-Commit Hook
===================

The ``git`` pre-commit hook automatically formats your Python files before they
are committed to your local repository. Any changes ``yapf`` makes to the files
will stay unstaged so that you can diff them manually.

To install, simply download the raw file and copy it into your git hooks directory:

.. code-block:: bash

    # From the root of your git project.
    curl -o https://raw.githubusercontent.com/google/yapf/master/plugins/pre-commit.sh
    mv pre-commit.sh .git/hooks/pre-commit
