Threaded_Wget
=============

This is a small utility that is able to parse a given URL and spawn a Wget thread for each individual file. 

The input URL is expected to be a directory list of the web folder.  This will not work if there is a default html document. 

This utility was designed for my personal use case.  As such it does not include many of the Wget commandline flags, only the ones I needed. 