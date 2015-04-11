" Copyright 2015 Google Inc. All Rights Reserved.
"
" Licensed under the Apache License, Version 2.0 (the "License");
" you may not use this file except in compliance with the License.
" You may obtain a copy of the License at
"
"     http://www.apache.org/licenses/LICENSE-2.0
"
" Unless required by applicable law or agreed to in writing, software
" distributed under the License is distributed on an "AS IS" BASIS,
" WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
" See the License for the specific language governing permissions and
" limitations under the License.
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
" VIM Autoload script for YAPF support
"
" Place this script in your ~/.vim/autoload directory. You can add accessors to
" ~/.vimrc, e.g.:
"
"    map <C-P> :call yapf#YAPF()<cr>
"    imap <C-P> <c-o>:call yapf#YAPF()<cr>
"
function! yapf#YAPF() range
  " Determine range to format.
  let l:line_ranges = a:firstline . '-' . a:lastline
  let l:cmd = 'yapf --lines=' . l:line_ranges

  " Call YAPF with the current buffer
  let l:formatted_text = system(l:cmd, join(getline(1, '$'), "\n") . "\n")

  " Update the buffer.
  execute '1,' . string(line('$')) . 'delete'
  call setline(1, split(l:formatted_text, "\n"))

  " Reset cursor to first line of the formatted range.
  call cursor(a:firstline, 1)
endfunction
