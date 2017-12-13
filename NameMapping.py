#!/usr/bin/env python

# 2017, Daniel Kirstenpfad
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

## This will take a legacy path in the form like:
##      /$id/images/$imagename.jpg
## and transform it to the name that is going to be used for the RIAK bucket name
##      $id
##
## Example:
## /fdaf16c657d997656bbccc5752eefa9f/images/1620028670_192497.jpg --> fdaf16c657d997656bbccc5752eefa9f/1620028670_192497.jpg
def legacyPathToRiakBucketName(Prefix, LegacyPath):
    # strip the trailing / if it is there
    if LegacyPath.startswith("/"):
        path_parts = LegacyPath[1:].split('/')
    else:
        path_parts = LegacyPath.split('/')
    # it needs to contain images as the second part and needs to be exactly 3 elements long
    if (len(path_parts) > 1):
        if (path_parts[1] == 'images') and (len(path_parts) >= 2):
            return str(Prefix)+str(path_parts[0])
        else:
            return None

## This will take a legacy path in the form like:
##      /id/images/$imagename.jpg
## and transform it to the key name that is going to be used for the RIAK bucket namespace
##      $imagename.jpg
##
## Example:
## /fdaf16c657d997656bbccc5752eefa9f/images/1620028670_192497.jpg --> 1620028670_192497.jpg
def legacyPathToRiakKeyName(LegacyPath):
    # strip the trailing / if it is there
    if LegacyPath.startswith("/"):
        path_parts = LegacyPath[1:].split('/')
    else:
        path_parts = LegacyPath.split('/')
    # it needs to contain images as the second part and needs to be exactly 3 elements long
    if (len(path_parts) > 1):
        if (path_parts[1] == 'images') and (len(path_parts) == 3):
            return str(path_parts[-1:][0])
        else:
            return None
