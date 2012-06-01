#!/usr/bin/env python
"""
FUSE-Gett: file system to directly access Ge.tt shares
"""
import logging

from collections import defaultdict
from errno import ENOENT
from stat import S_IFDIR, S_IFLNK, S_IFREG
from sys import argv, exit
from time import time

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

import requests
import simplejson as json

if not hasattr(__builtins__, 'bytes'):
    bytes = str

class Gett(LoggingMixIn, Operations):
    """ 
    Starting off based on the example memory filesystem.
    """
    apibase = "http://open.ge.tt"


    def __init__(self, apikey, email, password):
        jdata = json.dumps(dict(apikey=apikey, email=email, password=password))
        print "Connecting to Ge.tt"
        apitarget = "%s/1/users/login" %(self.apibase)
        req = requests.post(apitarget, data=jdata)
        if req.ok:
            print "Logged in!"
            res = json.loads(req.content)
            self.atoken = res['accesstoken']
            sharelist = self._getsharelist()
            self.spaceused, self.spacetotal = res['user']['storage']['used'], res['user']['storage']['limit']
        else:
            sharelist = []

        now = time()
        self.files = {}
        self.data = defaultdict(bytes)
        self.fd = 0
        self.files['/'] = dict(st_mode=(S_IFDIR | 0755), st_ctime=now,
                               st_mtime=now, st_atime=now, st_nlink=2)

        # Populate the directory with the share names
        for share in sharelist:
            sharename = share['sharename']
            dirname = share['title'] if "title" in share else sharename
            self.files["/%s" %(dirname)] = dict(st_mode=(S_IFDIR | 0755),
                                                st_ctime=share['created'],
                                                st_mtime=share['created'],
                                                st_atime=now,
                                                st_nlink=2,
                                                sharename=sharename,
                                                )
            for f in share['files']:
                filename = f['filename']
                size = f['size'] if 'size' in f else 0
                self.files["/%s/%s" %(dirname, filename)] = dict(st_mode=(S_IFREG | 0755),
                                                                 st_ctime=f['created'],
                                                                 st_mtime=f['created'],
                                                                 st_atime=now,
                                                                 st_nlink=1,
                                                                 st_size=size,
                                                                 sharename=sharename,
                                                                 fileid=f['fileid'],
                                                                 )
                self.files["/%s" %(dirname)]['st_nlink'] += 1
            self.files['/']['st_nlink'] += 1


    def _getsharelist(self):
        """ Get the list of shares for the logged in user """
        apitarget = "%s/1/shares?accesstoken=%s" %(self.apibase, self.atoken)
        req = requests.get(apitarget)
        result = json.loads(req.content) if req.ok else []
        return result

    def _getfile(self, sharename, fileid):
        """ Ge.tt API call to download a file """
        apitarget = "%s/1/files/%s/%s/blob" %(self.apibase, sharename, fileid)
        req = requests.get(apitarget)
        if req.ok:
            res = req.content
            print "Downloaded: ", sharename, fileid
        else:
            res = 0
        return res

    def _createshare(self, sharename):
        """ Ge.tt API call to create a new share """
        apitarget = "%s/1/shares/create?accesstoken=%s" %(self.apibase, self.atoken)
        jdata = json.dumps(dict(title=sharename))
        req = requests.post(apitarget, data=jdata)
        return req.ok

    def _destroyshare(self, sharename):
        """ Ge.tt API call to destroy a share """
        apitarget = "%s/1/shares/%s/destroy?accesstoken=%s" %(self.apibase, sharename, self.atoken)
        req = requests.post(apitarget)
        return req.ok

    def chmod(self, path, mode):
        self.files[path]['st_mode'] &= 0770000
        self.files[path]['st_mode'] |= mode
        return 0

    def chown(self, path, uid, gid):
        self.files[path]['st_uid'] = uid
        self.files[path]['st_gid'] = gid

    def create(self, path, mode):
        print("Create: %s" %(path))
        self.files[path] = dict(st_mode=(S_IFREG | mode), st_nlink=1,
                                st_size=0, st_ctime=time(), st_mtime=time(),
                                st_atime=time())

        self.fd += 1
        return self.fd

    def getattr(self, path, fh=None):
        if path not in self.files:
            raise FuseOSError(ENOENT)

        return self.files[path]

    def getxattr(self, path, name, position=0):
        attrs = self.files[path].get('attrs', {})

        try:
            return attrs[name]
        except KeyError:
            return ''       # Should return ENOATTR

    def listxattr(self, path):
        attrs = self.files[path].get('attrs', {})
        return attrs.keys()

    def mkdir(self, path, mode):
        """ Create a new directory, that is a new remote share """
        sharename = path[1:]
        res = self._createshare(sharename)
        if res:
            now = time()
            self.files["/%s" %(dirname)] = dict(st_mode=(S_IFDIR | 0755),
                                                st_ctime=now,
                                                st_mtime=now,
                                                st_atime=now,
                                                st_nlink=2,
                                                sharename=sharename,
                                                )
            self.files['/']['st_nlink'] += 1

    def open(self, path, flags):
        self.fd += 1
        return self.fd

    def read(self, path, size, offset, fh):
        """ Called when a file is read """
        # Download data if we haven't done that yet
        if path not in self.data:
            sharename, fileid = self.files[path]['sharename'], self.files[path]['fileid']
            binfile = self._getfile(sharename, fileid)
            self.data[path] = binfile
        return self.data[path][offset:offset + size]

    def readdir(self, path, fh):
        """ Read a directory, that is the files in a given share """
        # Currently working but low performance because we have to
        # scan the complete list of files
        pathlen = len(path)
        if path != '/':
            pathlen += 1
        result = ['.', '..']
        for x in self.files:
            if x == '/' or not x.startswith(path):
                continue
            print x[pathlen:]
            name = x[pathlen:].split('/')
            if len(name) == 1:
                result += [name[0]]
        return result

    def readlink(self, path):
        return self.data[path]

    def removexattr(self, path, name):
        attrs = self.files[path].get('attrs', {})

        try:
            del attrs[name]
        except KeyError:
            pass        # Should return ENOATTR

    def rename(self, old, new):
        self.files[new] = self.files.pop(old)

    def rmdir(self, path):
        """ Remove a directory, that is remove a remote share """
        target = self.files.pop(path)
        self.files['/']['st_nlink'] -= 1
        sharename = target['sharename']
        self._destroyshare(sharename)
        for f in self.files:
            if sharename in f and f['sharename'] == sharename:
                self.files.pop(f)

    def setxattr(self, path, name, value, options, position=0):
        # Ignore options
        attrs = self.files[path].setdefault('attrs', {})
        attrs[name] = value

    def statfs(self, path):
        """ Return file system use statistics, for example to be used with df """
        return dict(f_bsize=1024,  # block size (not sure if it makes a difference)
                    f_blocks=int(self.spacetotal/1024.0),  # max space available, 1K
                    f_bfree=int((self.spacetotal-self.spaceused)/1024.0),  # needed for correct "Used" count, 1K
                    f_bavail=int((self.spacetotal-self.spaceused)/1024.0),  # needed for correct "Available" count, 1K
                    )

    def symlink(self, target, source):
        self.files[target] = dict(st_mode=(S_IFLNK | 0777), st_nlink=1,
                                  st_size=len(source))

        self.data[target] = source

    def truncate(self, path, length, fh=None):
        self.data[path] = self.data[path][:length]
        self.files[path]['st_size'] = length

    def unlink(self, path):
        self.files.pop(path)

    def utimens(self, path, times=None):
        now = time()
        atime, mtime = times if times else (now, now)
        self.files[path]['st_atime'] = atime
        self.files[path]['st_mtime'] = mtime

    def write(self, path, data, offset, fh):
        self.data[path] = self.data[path][:offset] + data
        self.files[path]['st_size'] = len(self.data[path])
        return len(data)


if __name__ == '__main__':
    if len(argv) != 5:
        print('usage: %s <mountpoint> <apikey> <email> <passoword>' % argv[0])
        exit(1)

    mountpoint, apikey, username, password = argv[1:5]

    fuse = FUSE(Gett(apikey, username, password), mountpoint, foreground=True)
