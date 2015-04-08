===========
IDE Plugins
===========

VIM
===

The ``vim`` plugin allows you to reformat a range of code. Place it into the
``.vim/autoload`` directory. You can add key bindings in the ``.vimrc`` file:

.. code-block:: vim

    map <C-Y> :call yapf#YAPF()<cr>
    imap <C-Y> <c-o>:call yapf#YAPF()<cr>
