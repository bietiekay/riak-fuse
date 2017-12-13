# riak-fuse

## Introduction

This script acts as glue between a local file storage mount point and RIAK. It is targeted at specific use cases when local mount-points need to be migrated to RIAK without changing the applications accessing those mount point. Think of it as a transparent RIAK filesystem layer with multiple options to control it’s behavior regarding local files.

## Usage

The tool is started from command line or supervisord (see [supervisord] manual for further information how to set-up as daemon). It takes 2 parameters:

	riak-fuse.py -h

For a help text:
```
usage: riak-fuse.py [-h] -s SOURCE -t TARGET [-f] [-rp RIAKPORT]
                    [-rh RIAKHOST] [-rnp RIAK_NAMESPACE_PREFIX]
                    [-rdnp RIAK_DIRECTORY_NAMESPACE_PREFIX]
                    [-rbt RIAK_DIRECTORY_SET_BUCKETTYPE]
                    [-rdk RIAK_DIRECTORY_SET_DIRECTORYKEY]
                    [-rct RIAK_CONTENT_TYPE] [-dell] [-ddir] [-rreadcontent]
                    [-rreaddir] [-rfuid RIAK_CONTENTS_FILE_UID]
                    [-rfgid RIAK_CONTENTS_FILE_GID]

optional arguments:
  -h, --help            show this help message and exit
  -s SOURCE, --source SOURCE
                        the source mount point
  -t TARGET, --target TARGET
                        the target mount point
  -f, --foreground      don't go into background on start-up
  -rp RIAKPORT, --riakport RIAKPORT
                        the port RIAK PBC is listening on
  -rh RIAKHOST, --riakhost RIAKHOST
                        the host or IP adress RIAK PBC is listening on
  -rnp RIAK_NAMESPACE_PREFIX, --riak_namespace_prefix RIAK_NAMESPACE_PREFIX
                        the prefix given to each RIAK binary content bucket
  -rdnp RIAK_DIRECTORY_NAMESPACE_PREFIX, --riak_directory_namespace_prefix RIAK_DIRECTORY_NAMESPACE_PREFIX
                        the prefix given to each RIAK directory content bucket
  -rbt RIAK_DIRECTORY_SET_BUCKETTYPE, --riak_directory_set_buckettype RIAK_DIRECTORY_SET_BUCKETTYPE
                        the RIAK bucket type name used for directory content
                        buckets
  -rdk RIAK_DIRECTORY_SET_DIRECTORYKEY, --riak_directory_set_directorykey RIAK_DIRECTORY_SET_DIRECTORYKEY
                        the reserved key name of the directory listing set
  -rct RIAK_CONTENT_TYPE, --riak_content_type RIAK_CONTENT_TYPE
                        the mime type used for the RIAK binary content
  -dell, --delete_local
                        when present the local copy of a file shall be removed
                        when it was successfully transferred to RIAK
  -ddir, --disable_maintain_directory
                        when present the directory structure will NOT be
                        maintained in RIAK
  -rreadcontent, --use_riak_read_content
                        should the contents of RIAK be used to fulfill read
                        accesses to files
  -rreaddir, --use_riak_read_directory
                        should also the maintained RIAK datastructure be used
                        for directory read access
  -rfuid RIAK_CONTENTS_FILE_UID, --riak_contents_file_uid RIAK_CONTENTS_FILE_UID
                        the UID used for files when RIAK is used for read
                        directory access
  -rfgid RIAK_CONTENTS_FILE_GID, --riak_contents_file_gid RIAK_CONTENTS_FILE_GID
                        the GID used for files when RIAK is used for read
                        directory access
```

Where *source-mountpoint* is the mountpoint from where you migrate - essentially the local disk or mounted share that holds the current data-set.   The tool is acting only upon a certain path-scheme that is being in the following form: `/$foldername/images/*`

Every file matching the `*` is going to be handled by the script. Directories below that structure are not supported. Everything else is going to be ignored. This behavior is hard-coded and can be changed in the NameMapping.py files `legacyPath*` methods.

The *target-mountpoint* is the mount point where the tool will interact with the applications. It’s probably to replace the previously mounted *source-mountpoint*.

## Known issues / Unsupported behaviour
- hardlinks and symlinks are not supported and won't be supported
- renaming across buckets/merchants is not supported
- chown/chmod/setattr is not supported when RIAK is used for reading of files and directories
- subfolders are not supported beyond the matched path
- the directory set name must be named so that it does not collide with filenames/directory names inside that directory matching the pattern for this tool

## RIAK data structure details

### bucket and key naming

There are two buckets per merchant:
- Binary Content Bucket
	- here the file data / binary contents get stored
	- bucket name: `$riak_namespace_prefix$foldername`
		- so for a folder like: `/test/images/file.jpg` with default prefix it’ll have the bucket name `IMG_test`
	- the keys stored in this bucket are going to be named after the file part of the path
		- so for the bespoke example it’ll be `file.jpg`
	- for debugging:
		- to quickly get the contents of a bucket
			- `curl "http://localhost:8098/buckets/IMG_test/keys?keys=true" | python -m json.tool`
		- to get the contents of a file
			- `curl "http://localhost:8098/buckets/IMG_test/keys/file.jpg"`
- Directory Bucket
	- here the directory listing and file size information get stored
	- bucket name: `$riak_directory_namespace_prefix$foldername`
		- so for a folder like: `/test/images/file.jpg` with default prefix it’ll have the bucket name `IMGDIR_test`
	- the keys (sets) stored in this bucket holding the size information are named like the file part of the path. As a set they are only holding one piece of information (the size) for now.
		- so for bespoke example it’ll be `file.jpg` which contains a set of 1 piece of information which is the file size
	- in addition there’s a directory set holding a full directory listing of this directory. Each entry in the set is one file.
		- so for default values this key is named `directory`
	- for debugging:
		- to get the contents of a directory
			- `curl http://localhost:8098/types/sets/buckets/IMGDIR_test/datatypes/directory | python -m json.tool`
		- to get all buckets contents of a directory set bucket
			- `curl http://localhost:8098/types/sets/buckets/IMGDIR_test/keys?keys=true | python -m json.tool`
		- to get all available directory buckets
			- `curl http://localhost:8098/types/sets/buckets?buckets=true | python -m json.tool`

			## Local Build Instructions

			### Pre-requisites and dependencies
			- riak KV 2.1 or later
				- `apt-get install pkg-config libtool autoconf build-essentials gcc automake make libffi-dev libssl-dev openssl curl apt-transport-https libc6-dev-i386 libncurses5-dev fop xsltproc unixodbc-dev libpam0g-dev`
				- `curl -O https://raw.githubusercontent.com/spawngrid/kerl/master/kerl`
				- `chmod a+x kerl`
				- this installs Erlang
					- `./kerl build git git://github.com/basho/otp.git OTP_R16B02_basho8 R16B02-basho8`
				- this installs RIAK
					- `./kerl install R16B02-basho8 ~/erlang/R16B02-basho8`
				- this activates RIAK
					- `.~/erlang/R16B02-basho8/activate`
				- after RIAK is set-up and started
					- start using `riak-admin start`
					- add the required SETS bucket-type by running these commands:
						- `riak-admin bucket-type create sets '{"props":{"datatype":"set"}}'`
						- `riak-admin bucket-type activate sets`
			- fuse 2.9.3 or later
				- example set-up:
					- install build essentials:
						- `apt-get install pkg-config libtool autoconf build-essentials gcc automake make libffi-dev libssl-dev openssl curl apt-transport-https libc6-dev-i386`
					- get current source from https://github.com/libfuse/libfuse: `wget https://github.com/libfuse/libfuse/releases/download/fuse-2.9.7/fuse-2.9.7.tar.gz`
					- `tar xvf fuse-2.9.7.tar.gz`
					- `cd fuse-2.9.7`
					- `./configure`
					- `make -j8`
					- `make install`
			- python 2.7 or later
				- `apt-get install python python-pip`
			- libraries installed:
				- fusepy 2.0.4 or later (`pip install fusepy`)
				- RIAK KV 2.5.3 or later (`pip install riak`)

			### Set-Up

			Several aspects of this tool can and need to be configured (as in: changed in `riak-fuse.py`), as there is:
			- RIAK
				- Host/IP
					- default `riak_host = 'localhost'`
				- PBC port of RIAK
					- default: `riak_port = 8087`
				- Namespace Prefix for the file contents bucket
					- default: `riak_namespace_prefix = 'IMG_'`
				- Namespace Prefix for the directory bucket
					- default: `riak_directory_namespace_prefix = 'IMGDIR_'`
				- RIAK Bucket-Type to use for the directory bucket
					- default: `riak_directory_set_buckettype = 'sets'`
					- Note: This needed to be set-up earlier, see Pre-Requisites and Dependencies
				- RIAK directory bucket key name to store the directory listing in
					- default: `riak_directory_set_directorykey = 'directory'`
				- RIAK content value content type (better left unchanged for now)
					- default: `riak_content_type = 'application/octet-stream'`
			- Behavior Options
				- wether or not the local copy of a file shall be removed when it was successfully transferred to RIAK
					- default: `remove_local_copy_after_successful_mapping = False`
				- wether or not the directory structure will be maintained in RIAK
					- default: `maintain_riak_directory_structure = True`
				- should also the maintained RIAK directory data structure be used for directory read access (like listing files)
					- CHOWN/CHMOD and other attribute commands are ignored when enabled
					- local directory contents are ignored
					- default: `use_riak_directory_structure_for_read_access = False`
				- should the contents of RIAK be used to fulfill read accesses to files
					- default: `use_riak_file_contents_for_read_access = False`
				- File Permission Mask to be used when listing files from RIAK directory data structure
					- default: `riak_contents_file_mask = 0o777`
				- File GID and UID reported when listing directories / file status flags and information
					- default:
						- `riak_contents_file_uid = 0`
						- `riak_contents_file_gid = 0`
			- Logging Options
				- which log-level should be outputted as log
					- choose from: CRITICAL, ERROR, WARNING, INFO, DEBUG
					- default: `logger.setLevel(logging.ERROR)`

## Docker How-To

You can use docker to spawn a RIAK + riak-Fuse demo machine right away.

In order to do that run this to build the environment:

'docker-compose build riak-fuse'

To run:

'docker-compose run riak-fuse'

You now should be able to map the 22 port of the riak-fuse machine to whatever local port you feel good about and connect through SSH as user root with password root.

The riak-fuse script resides in /src/riak-fuse and you should call it from there.

For a brief demo - log in and go ahead and make a test:

check if riak is there:
'ping riak-kv'

now short demo:

'cd ~'
'mkdir source'
'mkdir source/test'
'mkdir source/test/images'
'mkdir target'
'/src/riak-fuse/riak-fuse.py -s ~/source/ -t ~/target/ -rh riak-kv -dell -rreaddir -rreadcontent'

you now should be able to generate files in ~/target/test/images - reading and writing.

Those get stored on riak-kv.

You can check if they are there by doing:

'echo "testcontent" >~/target/test/images/test.txt'

and get the dir-listing:

'curl "http://riak-kv:8098/buckets/IMG_test/keys?keys=true" | python -m json.tool'

and contents:


curl "http://riak-kv:8098/buckets/IMG_test/keys/test.txt"
