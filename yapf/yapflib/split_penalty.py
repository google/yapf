# Copyright 2022 Bill Wendling, All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from yapf.yapflib import style

# Generic split penalties
UNBREAKABLE = 1000**5
VERY_STRONGLY_CONNECTED = 5000
STRONGLY_CONNECTED = 2500

#############################################################################
# Grammar-specific penalties - should be <= 1000                            #
#############################################################################

# Lambdas shouldn't be split unless absolutely necessary or if
# ALLOW_MULTILINE_LAMBDAS is True.
LAMBDA = 1000
MULTILINE_LAMBDA = 500

ANNOTATION = 100
ARGUMENT = 25

# TODO: Assign real values.
RETURN_TYPE = 1
DOTTED_NAME = 40
EXPR = 10
DICT_KEY_EXPR = 20
DICT_VALUE_EXPR = 11
