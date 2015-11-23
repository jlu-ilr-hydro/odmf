#!/usr/bin/env python
# -*- coding:utf-8 -*-
'''
Created on 12.02.2012

@author: philkraf
'''
import sys
import os
from glob import glob

print sys.executable

from webpage import Root, HeapyPage
from webpage import lib
# Make autoreload
autoreload= not 'noreload' in sys.argv
print "autoreload =",autoreload

print "Kill session lock files"
for fn in glob('webpage/sessions/*.lock'):
    os.remove(fn)

# Create the URL root object
root=Root()

# Create a heapy page to view memory usage
if 'heapy' in sys.argv:
    print "Load heapy"
    from guppy import hpy
    hp=hpy()
    hp.setrelheap()
    root.heapy = HeapyPage(hp)
    
# Start the server
lib.start_server(root, autoreload=autoreload, port=8081)
