#!/usr/bin/env python

# this tool dumps a file (key_name parameter 2) from the given bucket (parameter 1)
#
# This takes two parameters:
#   parameter 1: the bucket name
#   parameter 2: the key name

import riak
import sys

if (len(sys.argv) == 2):
    print('Give 2 parameters: <bucket name> <key name>')
    print('Example:')
    print('        python riak-dump-file.py IMG_test 1.jpg')
    print('')
    print(' This will dump the 1.jpg key from the bucket IMG_test into the 1.jpg file.')
else:
    myClient = riak.RiakClient(pb_port=8087, protocol='pbc')
    photo_bucket = myClient.bucket(sys.argv[1])
    image_data_out = photo_bucket.get(sys.argv[2])
    # You've now got a ``RiakObject``. To get at the binary data, call:
    with open(sys.argv[2], 'wb') as f:
        binary_data = image_data_out.encoded_data
        f.write(binary_data)
