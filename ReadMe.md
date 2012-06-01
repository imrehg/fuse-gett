FUSE-Ge.tt
==========

FUSE [File System in Userspace][1] access to your [Ge.tt][2] shares. Eventually it will support adding and deleting shares and files, reliable upload, sharing and so on.

I'm not affiliated with Ge.tt in any ways, just making this to enhance their functionality for my requirements, and to play around with Python, fuse and [their API][5].

Requirements
============

[Python][3] and [fusepy][4].

Usage
=====

At this experimental stage, one has to [create an app][6] to receive an API key. Once that's done, the program can be called as:

    python fuse-gett.py <mount point> <api key> <user email> <password>

Here the email and password should probably be quoted (within " marks) to avoid problems with special characters.

Current functionality
=====================

 * Existing shares are loaded upon login
 * Files from existing shares can be accessed (copy, read, ...)
 * New shares can be created (but files cannot be uploaded yet)
 * Existing shares can be destroyed

Future functionality
====================

 * Full feature download and upload
 * Renaming shares, renaming files
 * Move files between shares
 * Real time updates (Live API)
 * Separate Ge.tt library for Python that can be included in other software

Contribution
============

Happy to receive any contribution, send me a message, or even better, a pull request that can be checked, discussed, and if it works, merged.

License
=======

See License.txt, basically simple MIT license.

 [1]: http://fuse.sourceforge.net/ "FUSE homepage"
 [2]: http://ge.tt "Ge.tt homepage"
 [3]: http://www.python.org "Python homepage"
 [4]: https://github.com/terencehonles/fusepy "fusepy on Github"
 [5]: https://open.ge.tt/1/doc/rest "Ge.tt REST API"
 [6]: http://ge.tt/developers/create "Create app on Ge.tt"
