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
" VIM command for YAPF support
"
" Place this script in your ~/.vim/plugin directory. You can call the
" command YAPF. If you omit the range, it will reformat the whole
" buffer.
"
" example:
"   :YAPF       " formats whole buffer
"   :'<,'>YAPF  " formats lines selected in visual mode

command! -range=% YAPF <line1>,<line2>call yapf#YAPF()
