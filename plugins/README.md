# IDE Plugins

## Emacs

The `Emacs` plugin is maintained separately. Installation directions can be
found here: https://github.com/paetzke/py-yapf.el


## Vim

The `vim` plugin allows you to reformat a range of code. Copy `plugin` and
`autoload` directories into your `~/.vim` or use `:packadd` in Vim 8. Or use
a plugin manager like Plug or Vundle:

```vim
" Plug
Plug 'google/yapf', { 'rtp': 'plugins/vim', 'for': 'python' }

" Vundle
Plugin 'google/yapf', { 'rtp': 'plugins/vim' }
```

You can add key bindings in the `.vimrc` file:

```vim
map <C-Y> :call yapf#YAPF()<cr>
imap <C-Y> <c-o>:call yapf#YAPF()<cr>
```

Alternatively, you can call the command `YAPF`. If you omit the range, it will
reformat the whole buffer.

example:

```vim
:YAPF       " formats whole buffer
:'<,'>YAPF  " formats lines selected in visual mode
```


## Sublime Text

The `Sublime Text` plugin is also maintained separately. It is compatible with
both Sublime Text 2 and 3.

The plugin can be easily installed by using *Sublime Package Control*. Check
the project page of the plugin for more information: https://github.com/jason-kane/PyYapf


## git Pre-Commit Hook

The `git` pre-commit hook automatically formats your Python files before they
are committed to your local repository. Any changes `yapf` makes to the files
will stay unstaged so that you can diff them manually.

To install, simply download the raw file and copy it into your git hooks
directory:

```bash
# From the root of your git project.
$ curl -o pre-commit.sh https://raw.githubusercontent.com/google/yapf/main/plugins/pre-commit.sh
$ chmod a+x pre-commit.sh
$ mv pre-commit.sh .git/hooks/pre-commit
```


## Textmate 2

Plugin for `Textmate 2` requires `yapf` Python package installed on your
system:

```bash
$ pip install yapf
```

Also, you will need to activate `Python` bundle from `Preferences > Bundles`.

Finally, create a `~/Library/Application Support/TextMate/Bundles/Python.tmbundle/Commands/YAPF.tmCommand`
file with the following content:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>beforeRunningCommand</key>
  <string>saveActiveFile</string>
  <key>command</key>
  <string>#!/bin/bash

TPY=${TM_PYTHON:-python}

"$TPY" "/usr/local/bin/yapf" "$TM_FILEPATH"</string>
  <key>input</key>
  <string>document</string>
  <key>name</key>
  <string>YAPF</string>
  <key>scope</key>
  <string>source.python</string>
  <key>uuid</key>
  <string>297D5A82-2616-4950-9905-BD2D1C94D2D4</string>
</dict>
</plist>
```

You will see a new menu item `Bundles > Python > YAPF`.
