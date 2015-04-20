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
``.vim/autoload`` directory. You can add key bindings in the ``.vimrc`` file:

.. code-block:: vim

    map <C-Y> :call yapf#YAPF()<cr>
    imap <C-Y> <c-o>:call yapf#YAPF()<cr>
