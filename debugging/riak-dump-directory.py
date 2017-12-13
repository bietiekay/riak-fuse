#!/usr/bin/env python

# this tool dumps the directory listing of a specified merchant directory bucket to STDOUT
#
# This takes two parameters:
#   parameter 1: the bucket name

import riak
import sys
import riak.datatypes as datatypes

if (len(sys.argv) == 1):
    print('Give 1 parameters: <bucket name>')
    print('Example:')
    print('        python riak-dump-directory.py IMGDIR_test')
    print('')
    print('This will dump the IMGDIR_test directories contents to STDOUT')
else:
    btype = riak.RiakClient(pb_port=8087, protocol='pbc').bucket_type('sets')
    bucket = btype.bucket(sys.argv[1])
    myset = datatypes.Set(bucket, 'directory')
    myset.reload()

    for id in myset:
        print('%s'% (id))
