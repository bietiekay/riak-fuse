#!/usr/bin/env python
#
# see readme.md for further details on running this.
#
# 	riak-fuse.py -h
#
# This fuse script also uses the RIAK 2 datatype "set" --> make sure to run:
#   riak-admin bucket-type create sets '{"props":{"datatype":"set"}}'
#   riak-admin bucket-type activate sets
#
# Not-Supported:
#   - hardlinks and symlinks are not supported and won't be supported
#   - renaming across buckets is not supported
#   - chown/chmod/setattr is not supported when RIAK is used for reading of files and directories
#   - subfolders are not supported beyond the matched path

from __future__ import with_statement

import os
import sys
import errno
import logging
import riak
import argparse
import NameMapping
from time import time
from stat import S_IFDIR, S_IFLNK, S_IFREG
from fuse import FUSE, FuseOSError, Operations
import riak.datatypes as datatypes

# Log related
logger = logging.getLogger('root')
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# create console handler and set level to debug
ch = logging.StreamHandler()
# add formatter to ch
ch.setFormatter(log_formatter)
# add ch to logger
logger.addHandler(ch)

class riakfuse(Operations):
    def __init__(self, root):
        self.root = root

    # Helpers
    # =======

    def _full_path(self, partial):
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(self.root, partial)
        return path

    def pathYieldGenerator():
        mylist = range(3)
        for i in mylist:
            yield i*i

    # ==================
    # Filesystem methods
    # ==================
    def access(self, path, mode):
        full_path = self._full_path(path)
        logger.debug('access %s - mode: %s'% (path,mode))
        # always return successfully on write
        if (mode == 2):
            return

        if not os.access(full_path, mode):
            raise FuseOSError(errno.EACCES)

    def chmod(self, path, mode):
        full_path = self._full_path(path)
        logger.debug('chmod %s - mode: %s'% (path,mode))
        if (use_riak_file_contents_for_read_access):
            logger.debug('since riak being used for read calls - chmod is ignored')
            return
        else:
            return os.chmod(full_path, mode)

    def chown(self, path, uid, gid):
        full_path = self._full_path(path)
        logger.debug('chown %s - uid: %s gid: %s'% (path,uid,gid))
        return os.chown(full_path, uid, gid)

    def getattr(self, path, fh=None):
        full_path = self._full_path(path)
        logger.debug('getattr %s'% (path))
        if (use_riak_file_contents_for_read_access):
            RiakDirectoryBucketNamespace = NameMapping.legacyPathToRiakBucketName(riak_directory_namespace_prefix,path)
            RiakKeyNamespace = NameMapping.legacyPathToRiakKeyName(path)
            if RiakKeyNamespace is None:
                # apparently this is not a proper path, so just go ahead and unlink the local file and report on that
                logger.warning('%s is not a mappable RIAK bucket - ignoring.'% (path))
                # so ignore...
                st = os.lstat(full_path)
            else:
                # we got a valid path, now just return the default file mask
                #st = os.lstat('/etc/passwd')
                #check if it is existing by trying to get it's size from the value stored under the file key in the directory bucket
                logger.debug('Retrieving stored object size and status...%s/%s'% (RiakDirectoryBucketNamespace,RiakKeyNamespace))
                # read the set contents...
                btype = riak.RiakClient(host=riak_host, pb_port=riak_port, protocol='pbc').bucket_type('sets')
                bucket = btype.bucket(RiakDirectoryBucketNamespace)
                myset = datatypes.Set(bucket, RiakKeyNamespace)
                myset.reload()
                if len(myset) > 0:
                    the_file_size = int(next(iter(myset)))
                    logger.debug('Got size: %s'% (str(the_file_size)))
                else:
                    the_file_size = None

                if (the_file_size is None):
                    logger.debug('Requested file %s apparently not existing in %s checking locally...'% (RiakKeyNamespace,RiakDirectoryBucketNamespace))
                    if os.path.isfile(full_path):
                        logger.debug('file exists locally - using this one...(%s)'% (full_path))
                        return dict(st_mode=(S_IFREG | riak_contents_file_mask), st_nlink=1, st_uid=riak_contents_file_uid, st_gid=riak_contents_file_gid, st_size=os.path.getsize(full_path), st_ctime=time(), st_mtime=time(),st_atime=time())
                    else:
                        raise FuseOSError(errno.ENOENT)
                else:
                    # You've now got a ``RiakObject``. To get at the binary data, call:
                    return dict(st_mode=(S_IFREG | riak_contents_file_mask), st_nlink=1, st_uid=riak_contents_file_uid, st_gid=riak_contents_file_gid, st_size=the_file_size, st_ctime=time(), st_mtime=time(),st_atime=time())
        else:
            st = os.lstat(full_path)

        logger.debug('Attributes: %s'% (st))
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime','st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

    def readdir(self, path, fh):
        full_path = self._full_path(path)
        logger.debug('readdir %s - fh: %s'% (path,fh))
        dirents = ['.', '..']
        # generate the correct names for the buckets and keys
        RiakDirectoryBucketNamespace = NameMapping.legacyPathToRiakBucketName(riak_directory_namespace_prefix,path)

        if (use_riak_directory_structure_for_read_access) and (RiakDirectoryBucketNamespace is not None):
            try:
                logger.debug('using RIAK directory structure in %s (for %s)'% (RiakDirectoryBucketNamespace,path))
                # Updating the $prefix+$id+$directoryprefix set with the given information
                # we shall use our own riak client instance for this
                btype = riak.RiakClient(host=riak_host, pb_port=riak_port, protocol='pbc').bucket_type(riak_directory_set_buckettype)
                # get the bucket for the directory namespace - this is a sets pre-configured bucket
                bucket = btype.bucket(RiakDirectoryBucketNamespace)
                # get the correct key inside that bucket
                myset = datatypes.Set(bucket, riak_directory_set_directorykey)
                # fetch the directory in order to be able to output it...
                myset.reload()
                for r in dirents:
                    yield r

                for id in myset:
                    yield id
            except Exception as e:
                # throw controlled exception
                logger.error('ERROR retrieving directory structure on RIAK bucket %s (Exception: %s)'% (RiakDirectoryBucketNamespace,str(e)))
                raise FuseOSError(errno.EACCES)
        else:
            # this is not a valid namespace - so pattern did not match on a directory/filename structure known to be mapped
            # --> therefore this method will return to the caller now.
            if RiakDirectoryBucketNamespace is None:
                # apparently this is not a proper path, so just go ahead and unlink the local file and report on that
                logger.warning('%s is not a mappable RIAK bucket - ignoring.'% (path))

            # take local information instead
            if os.path.isdir(full_path):
                dirents.extend(os.listdir(full_path))
            for r in dirents:
                yield r

    def mknod(self, path, mode, dev):
        logger.debug('mknod %s - mode: %s dev: %s'% (path,mode,dev))
        return os.mknod(self._full_path(path), mode, dev)

    def rmdir(self, path):
        full_path = self._full_path(path)
        logger.debug('rmdir %s'% (path))
        return os.rmdir(full_path)

    def mkdir(self, path, mode):
        logger.debug('mkdir %s - mode: %s'% (path,mode))
        return os.mkdir(self._full_path(path), mode)

    def statfs(self, path):
        full_path = self._full_path(path)
        logger.debug('statfs %s'% (path))
        stv = os.statvfs(full_path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))

    def rename(self, old, new):
        logger.debug('rename %s - target: %s'% (old,new))
        if (maintain_riak_directory_structure):
            # check if this is the directory that matches our patterns
            try:
                # generate the correct names for the buckets and keys
                RiakBucketNamespace = NameMapping.legacyPathToRiakBucketName(riak_namespace_prefix,old)
                RiakNewBucketNamespace = NameMapping.legacyPathToRiakBucketName(riak_namespace_prefix,new)
                RiakKeyNamespace = NameMapping.legacyPathToRiakKeyName(old)
                RiakNewKeyNamespace = NameMapping.legacyPathToRiakKeyName(new)
                RiakDirectoryBucketNamespace = NameMapping.legacyPathToRiakBucketName(riak_directory_namespace_prefix,old)
                RiakDirectoryNewBucketNamespace = NameMapping.legacyPathToRiakBucketName(riak_directory_namespace_prefix,new)
                logger.debug('rename %s %s %s %s'% (RiakKeyNamespace, RiakNewKeyNamespace, RiakDirectoryBucketNamespace, RiakDirectoryNewBucketNamespace))
                # only continue of the Bucket Names match, not supported to rename between buckets
                if (RiakDirectoryBucketNamespace == RiakDirectoryNewBucketNamespace):
                    # this is not a valid namespace - so pattern did not match on a directory/filename structure known to be mapped
                    # --> therefore this method will return to the caller now.
                    if RiakKeyNamespace is None:
                        # apparently this is not a proper path, so just go ahead and unlink the local file and report on that
                        logger.warning('%s is not a mappable RIAK bucket - ignoring.'% (old))
                        # so do the local rename anways...
                        return os.rename(self._full_path(old), self._full_path(new))

                    logger.debug('updating %s directory structure for %s to %s (renaming)'% (RiakDirectoryBucketNamespace,RiakKeyNamespace, RiakNewKeyNamespace))
                    # Updating the $prefix+$id+$directoryprefix set with the given information
                    # we shall use our own riak client instance for this
                    btype = riak.RiakClient(host=riak_host, pb_port=riak_port, protocol='pbc').bucket_type(riak_directory_set_buckettype)
                    # get the bucket for the directory namespace - this is a sets pre-configured bucket
                    bucket = btype.bucket(RiakDirectoryBucketNamespace)
                    # get the correct key inside that bucket
                    myset = datatypes.Set(bucket, riak_directory_set_directorykey)
                    # fetch the directory in order to be change it...
                    myset.reload()
                    # add this file to the directory - if it's already there it won't be added (handled by RIAK)
                    myset.discard(RiakKeyNamespace)
                    myset.add(RiakNewKeyNamespace)
                    # send to RIAK afterall
                    myset.store()
                    logger.debug('DONE updating RIAK directory structure')

                    # create RiakClient instance
                    riakClient = riak.RiakClient(host=riak_host, pb_port=riak_port, protocol='pbc')
                    # get the correct bucket
                    old_bucket = riakClient.bucket(RiakBucketNamespace)
                    new_bucket = riakClient.bucket(RiakNewBucketNamespace)
                    # read the old key contents...
                    the_imge_data = old_bucket.get(RiakKeyNamespace)
                    logger.debug('Got the old key contents from RIAK (%s/%s)'% (RiakBucketNamespace,RiakKeyNamespace))
                    # and write those to the new bucket...
                    riak_image = new_bucket.new(RiakNewKeyNamespace, encoded_data=the_imge_data, content_type=riak_content_type)
                    logger.debug('Wrote contents to RIAK %s'% (RiakNewKeyNamespace))
                    # remove the old one...
                    old_bucket.delete(RiakKeyNamespace)
                    logger.debug('Removed old key from RIAK %s'% (RiakKeyNamespace))
                    # send to RIAK afterall
                    riak_image.store()
                    # if the local copy is removed, it's gone anyways...
                    if not (remove_local_copy_after_successful_mapping):
                        # we shall now rename the local file and finish...
                        return os.rename(self._full_path(old), self._full_path(new))
                else:
                    logger.debug('ERROR unsupported rename of file between buckets (%s -> %s)'% (RiakDirectoryBucketNamespace,RiakDirectoryNewBucketNamespace))
                    raise FuseOSError(errno.ENOTSUP)
            except Exception as e:
                # throw controlled exception but do not remove the actual local file due to errors in the process...
                logger.error('ERROR updating directory structure on RIAK bucket %s the key %s (Exception: %s)'% (RiakDirectoryBucketNamespace,RiakKeyNamespace,str(e)))
                raise FuseOSError(errno.EACCES)
        else:
            # go ahead and rename locally
            return os.rename(self._full_path(old), self._full_path(new))

    def utimens(self, path, times=None):
        logger.debug('utimens %s'% (path))
        return os.utime(self._full_path(path), times)

    # ============
    # File methods
    # ============

    def open(self, path, flags):
        full_path = self._full_path(path)
        logger.debug('open %s - flags: %s'% (path,flags))

        # when we're reading from RIAK, we're going to retrieve the file contents from RIAK and store it locally for temporary use
        if (use_riak_file_contents_for_read_access):
            RiakBucketNamespace = NameMapping.legacyPathToRiakBucketName(riak_namespace_prefix,path)
            RiakKeyNamespace = NameMapping.legacyPathToRiakKeyName(path)

            if RiakKeyNamespace is None:
                # apparently this is not a proper path, so just go ahead and unlink the local file and report on that
                logger.warning('%s is not a mappable RIAK bucket - ignoring.'% (path))
                # so do the local rename anways...
                return os.open(full_path, flags)
            try:
                logger.debug('Retrieving key contents and storing temporarily...%s/%s'% (RiakBucketNamespace,RiakKeyNamespace))
                # create RiakClient instance
                riakClient = riak.RiakClient(host=riak_host, pb_port=riak_port, protocol='pbc')
                # get the correct bucket
                bucket = riakClient.bucket(RiakBucketNamespace)
                # read the old key contents...
                the_imge_data = bucket.get(RiakKeyNamespace)
                # You've now got a ``RiakObject``. To get at the binary data, call:
                with open(full_path, 'wb') as f:
                    binary_data = the_imge_data.encoded_data
                    f.write(binary_data)
            except Exception as e:
                # throw controlled exception but do not remove the actual local file due to errors in the process...
                logger.error('ERROR retrieving data from RIAK bucket %s the key %s (Exception: %s)'% (RiakBucketNamespace,RiakKeyNamespace,str(e)))
                raise FuseOSError(errno.EACCES)
            else:
                logger.debug('DONE Got the old key contents from RIAK (%s/%s) and stored temporarily %s'% (RiakBucketNamespace,RiakKeyNamespace,full_path))
        return os.open(full_path, flags)

    def create(self, path, mode, fi=None):
        full_path = self._full_path(path)
        logger.debug('create %s - mode: %s'% (path,mode))
        return os.open(full_path, os.O_WRONLY | os.O_CREAT, mode)

    def read(self, path, length, offset, fh):
        logger.debug('read %s - length: %s offset: %s fh: %s'% (path, length, offset, fh))
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)

    def write(self, path, buf, offset, fh):
        logger.debug('write %s - length: %s offset: %s fh: %s'% (path, sys.getsizeof(buf), offset, fh))
        os.lseek(fh, offset, os.SEEK_SET)
        return os.write(fh, buf)

    def truncate(self, path, length, fh=None):
        full_path = self._full_path(path)
        logger.debug('truncate %s - length: %s'% (path,length))
        with open(full_path, 'r+') as f:
            f.truncate(length)

    def flush(self, path, fh):
        logger.debug('flush %s - fh: %s'% (path,fh))
        return os.fsync(fh)

    def fsync(self, path, fdatasync, fh):
        logger.debug('fsync %s - fdatasync: %s fh: %s'% (path,fdatasync,fh))
        return self.flush(path, fh)

    # unlink is called whenever a file is removed. Since we're maintaining a
    def unlink(self, path):
        logger.debug('unlink path %s'% (path))

        # all Riak interactions only necessary when this module actually is managing directory structures in RIAK
        if (maintain_riak_directory_structure):
            try:
                # generate the correct names for the buckets and keys
                RiakBucketNamespace = NameMapping.legacyPathToRiakBucketName(riak_namespace_prefix,path)
                RiakKeyNamespace = NameMapping.legacyPathToRiakKeyName(path)
                RiakDirectoryBucketNamespace = NameMapping.legacyPathToRiakBucketName(riak_directory_namespace_prefix,path)

                # this is not a valid namespace - so pattern did not match on a directory/filename structure known to be mapped
                # --> therefore this method will return to the caller now.
                if RiakKeyNamespace is None:
                    # apparently this is not a proper path, so just go ahead and unlink the local file and report on that
                    logger.warning('%s is not a mappable RIAK bucket - ignoring.'% (path))
                    return os.unlink(self._full_path(path))

                logger.debug('updating %s directory structure for %s (discarding)'% (RiakDirectoryBucketNamespace,RiakKeyNamespace))
                # Updating the $prefix+$id+$directoryprefix set with the given information
                # we shall use our own riak client instance for this
                btype = riak.RiakClient(host=riak_host, pb_port=riak_port, protocol='pbc').bucket_type(riak_directory_set_buckettype)
                # get the bucket for the directory namespace - this is a sets pre-configured bucket
                bucket = btype.bucket(RiakDirectoryBucketNamespace)
                # get the correct key inside that bucket
                myset = datatypes.Set(bucket, riak_directory_set_directorykey)
                # fetch the directory in order to be change it...
                myset.reload()
                # add this file to the directory - if it's already there it won't be added (handled by RIAK)
                myset.discard(RiakKeyNamespace)

                mysizeset = datatypes.Set(bucket, RiakKeyNamespace) # this is the set
                mysizeset.reload()
                logger.debug('SizeSet len %s'% (len(mysizeset)))
                if len(mysizeset) > 0:
                    the_file_size = int(next(iter(mysizeset)))
                    logger.debug('Discarding object size %s in riak %s'% (the_file_size,RiakKeyNamespace))
                    mysizeset.discard(str(the_file_size))

                # send to RIAK afterall
                #logger.debug('Storing directory structure...')
                myset.store()
                #logger.debug('Storing size structure...')
                mysizeset.store()
                logger.debug('DONE updating directory structure')
                # now update the bucket itself by removing the key
                # create RiakClient instance
                riakClient = riak.RiakClient(host=riak_host, pb_port=riak_port, protocol='pbc')
                # get the correct bucket
                release_bucket = riakClient.bucket(RiakBucketNamespace)
                # remove that key
                release_bucket.delete(RiakKeyNamespace)
            except Exception as e:
                # throw controlled exception but do not remove the actual local file due to errors in the process...
                logger.error('ERROR updating directory structure on RIAK bucket %s the key %s (Exception: %s)'% (RiakDirectoryBucketNamespace,RiakKeyNamespace,str(e)))
                raise FuseOSError(errno.EACCES)

        # finally do the local unlink when all of the above where successful
        if (os.path.exists(self._full_path(path))):
            return os.unlink(self._full_path(path))
        else:
            return

    # release is called everytime a file is closed by a client application. This module does most of it's work
    # in this release call.
    # This is when the file is closed by the process that accessed it. Wether it has been written or not, we do not care right now
    # if it's released, it'll be pushed to the bucket in Riak
    def release(self, path, fh):
        logger.debug('release %s - fh: %s'% (path,fh))

        # First step: get the correct names for buckets and keys
        RiakBucketNamespace = NameMapping.legacyPathToRiakBucketName(riak_namespace_prefix,path)
        RiakKeyNamespace = NameMapping.legacyPathToRiakKeyName(path)
        RiakDirectoryBucketNamespace = NameMapping.legacyPathToRiakBucketName(riak_directory_namespace_prefix,path)

        # this is not a valid namespace - so pattern did not match on a directory/filename structure known to be mapped
        # --> therefore this method will return to the caller now.
        if RiakBucketNamespace is None:
            # apparently this is not a proper path, so just go ahead and close the handle but report
            logger.warning('%s is not a mappable RIAK bucket - ignoring.'% (path))
            return os.close(fh)

        # this seems to be a mappable RIAK path - so let's log and move on to actually moving the file to RIAK
        logger.debug('updating on RIAK bucket %s the key %s (%s bytes to write.)'% (RiakBucketNamespace,RiakKeyNamespace,os.path.getsize(self._full_path(path))))

        try:
            # create RiakClient instance
            riakClient = riak.RiakClient(host=riak_host, pb_port=riak_port, protocol='pbc')
            # get the correct bucket
            release_bucket = riakClient.bucket(RiakBucketNamespace)
            # open the local file for read access off the filesystem
            the_imge_data = open(self._full_path(path), 'rb').read()
            # get the key+value and add it to the bucket
            riak_image = release_bucket.new(RiakKeyNamespace, encoded_data=the_imge_data, content_type=riak_content_type)
            # send to RIAK afterall
            riak_image.store()
        except Exception as e:
            logger.error('ERROR updating on RIAK bucket %s the key %s (Exception: %s)'% (RiakBucketNamespace,RiakKeyNamespace,str(e)))
        else:
            logger.debug('DONE updating on RIAK bucket %s the key %s'% (RiakBucketNamespace,RiakKeyNamespace))
            # is the directory structure (also) maintained in RIAK - if so, go ahead and update properly
            if (maintain_riak_directory_structure):
                logger.debug('updating %s directory structure for %s'% (RiakDirectoryBucketNamespace,RiakKeyNamespace))
                # Updating the $prefix+$id+$directoryprefix set with the given information
                # we shall use our own riak client instance for this
                btype = riak.RiakClient(host=riak_host, pb_port=riak_port, protocol='pbc').bucket_type(riak_directory_set_buckettype)
                # get the bucket for the directory namespace - this is a sets pre-configured bucket
                bucket = btype.bucket(RiakDirectoryBucketNamespace)
                # get the correct key inside that bucket
                myset = datatypes.Set(bucket, riak_directory_set_directorykey)
                # add this file to the directory - if it's already there it won't be added (handled by RIAK)
                myset.add(RiakKeyNamespace)

                logger.debug('updating size (%s) entry in directory %s/%s'% (str(os.stat(self._full_path(path)).st_size),RiakDirectoryBucketNamespace,RiakKeyNamespace))
                btype.bucket(RiakDirectoryBucketNamespace).new(RiakKeyNamespace, encoded_data=str(os.stat(self._full_path(path)).st_size), content_type=riak_content_type)
                mysizeset = datatypes.Set(bucket, RiakKeyNamespace)
                mysizeset.add(str(os.stat(self._full_path(path)).st_size))

                # send to RIAK afterall
                myset.store()
                mysizeset.store()
                logger.debug('DONE updating directory structure')
            # should the local copy of the file be removed or not
            if (remove_local_copy_after_successful_mapping):
                logger.debug('removing local copy %s'% (path))
                # first close it
                returnvalueclose = os.close(fh)
                # then remove it (just locally)
                os.unlink(self._full_path(path))
                # return the correct return value as per close
                return returnvalueclose
            else:
                logger.debug('not removing local copy %s'% (path))
                return os.close(fh)
    #################################### partially supported methods
    def readlink(self, path):
        logger.debug('readlink %s'% (path))
        RiakBucketNamespace = NameMapping.legacyPathToRiakBucketName(riak_namespace_prefix,path)

        if RiakBucketNamespace is None:
            logger.debug('%s is not a mappable RIAK bucket - therefore readlink is supported '% (path))
            pathname = os.readlink(self._full_path(path))
            logger.debug('Readlink Path %s'% (pathname))
            if pathname.startswith("/"):
                # Path name is absolute, sanitize it.
                return pathname
                #os.path.relpath(pathname, self.root)
            else:
                return pathname
        else:
            logger.warning('readlink is not supported on RIAK usage %s'% (path))
            raise FuseOSError(errno.ENOTSUP)

    #################################### Unsupported Methods

    def symlink(self, name, target):
        logger.debug('symlink %s - target: %s'% (name,target))
        logger.warning('symlink call is not supported')
        raise FuseOSError(errno.ENOTSUP)

    def link(self, path, target):
        logger.debug('link %s - target: %s'% (path,target))
        logger.warning('link call is not supported')
        raise FuseOSError(errno.ENOTSUP)
    ########################################################

def main(mountpoint, root, daemonize):
    logger.info("Starting up RIAKfuse...")
    FUSE(riakfuse(root), mountpoint, nothreads=True, foreground=daemonize)

if __name__ == '__main__':
    riak_port = 8087
    parser = argparse.ArgumentParser(description='This script acts as glue between a local file storage mount point and RIAK. It\'s targeted at specific use cases when local mount-points need to be migrated to RIAK without changing the applications accessing those mount point. Think of it as a transparent RIAK filesystem layer with multiple options to control it\'s behavior regarding local files.')
    parser.add_argument('-s','--source', help='the source mount point', type=str, required=True)
    parser.add_argument('-t','--target', help='the target mount point', type=str, required=True)
    parser.add_argument('-f','--foreground', help='don\'t go into background on start-up', dest='foreground', action='store_true', default=False, required=False)
    parser.add_argument('-rp','--riakport', help='the port RIAK PBC is listening on', type=int, default=8087 , required=False)
    parser.add_argument('-rh','--riakhost', help='the host or IP adress RIAK PBC is listening on', type=str, default='localhost' , required=False)
    parser.add_argument('-rnp','--riak_namespace_prefix', help='the prefix given to each RIAK binary content bucket', type=str, default='IMG_' , required=False)
    parser.add_argument('-rdnp','--riak_directory_namespace_prefix', help='the prefix given to each RIAK directory content bucket', type=str, default='IMGDIR_' , required=False)
    parser.add_argument('-rbt','--riak_directory_set_buckettype', help='the RIAK bucket type name used for directory content buckets', type=str, default='sets' , required=False)
    parser.add_argument('-rdk','--riak_directory_set_directorykey', help='the reserved key name of the directory listing set', type=str, default='directory' , required=False)
    parser.add_argument('-rct','--riak_content_type', help='the mime type used for the RIAK binary content', type=str, default='application/octet-stream' , required=False)
    parser.add_argument('-dell','--delete_local', help='when present the local copy of a file shall be removed when it was successfully transferred to RIAK', dest='delete_local', action='store_true', default=False , required=False)
    parser.add_argument('-ddir','--disable_maintain_directory', help='when present the directory structure will NOT be maintained in RIAK', dest='disable_maintain_directory', action='store_false', default=True , required=False)
    parser.add_argument('-rreadcontent','--use_riak_read_content', help='should the contents of RIAK be used to fulfill read accesses to files', dest='use_riak_read_content', action='store_true', default=False , required=False)
    parser.add_argument('-rreaddir','--use_riak_read_directory', help='should also the maintained RIAK datastructure be used for directory read access', dest='use_riak_read_directory', action='store_true', default=False , required=False)
    parser.add_argument('-rfuid','--riak_contents_file_uid', help='the UID used for files when RIAK is used for read directory access', type=int, default=0 , required=False)
    parser.add_argument('-rfgid','--riak_contents_file_gid', help='the GID used for files when RIAK is used for read directory access', type=int, default=0 , required=False)
    args = vars(parser.parse_args())

    ##################################################################################################
    # configuration
    ##################################################################################################
    logger.debug('Source mount point: %s'% (args['source']))
    logger.debug('Target mount point: %s'% (args['target']))

    # RIAK related
    riak_port = args['riakport']
    riak_host = args['riakhost']
    riak_namespace_prefix = args['riak_namespace_prefix']
    riak_directory_namespace_prefix = args['riak_directory_namespace_prefix']
    riak_directory_set_buckettype = args['riak_directory_set_buckettype']
    riak_directory_set_directorykey = args['riak_directory_set_directorykey']
    riak_content_type = args['riak_content_type']

    # Options / Flags
    remove_local_copy_after_successful_mapping = args['delete_local']       # wether or not the local copy of a file shall be removed when it was successfully transferred to RIAK, default=False
    maintain_riak_directory_structure = args['disable_maintain_directory']                 # wether or not the directory structure will be maintained in RIAK, default=True
    use_riak_directory_structure_for_read_access = args['use_riak_read_directory']     # should also the maintained RIAK datastructure be used for directory read access, default=False
    use_riak_file_contents_for_read_access = args['use_riak_read_content']           # should the contents of RIAK be used to fulfill read accesses to files, default=False
    riak_contents_file_mask = 0o777
    riak_contents_file_uid = args['riak_contents_file_uid']
    riak_contents_file_gid = args['riak_contents_file_gid']
    logger.setLevel(logging.DEBUG)

    # call main with parameters set
    main(args['target'], args['source'],  args['foreground'])
