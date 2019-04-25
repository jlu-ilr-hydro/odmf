# !/usr/bin/env python
# -*- coding:utf-8 -*-
'''
Created on 12.02.2012

@author: philkraf
'''
import sys
sys.path.insert(0,'..')
import os
from glob import glob

from odmf.tools.parseConf import parseConf

print("Starting schwingbachserver using {}".format(sys.executable))

if sys.version_info[0] < 3:
    raise Exception("Must be using Python 3")

# System checks !before project imports
import odmf.conf as conf
try:
    # Check for mandatory attributes
    parseConf(conf)
    print("✔ Config is valid")
except Exception as e:
    print("Error in config validation: {}".format(e))
    exit(1)


# Start with project imports
from odmf.webpage import Root, HeapyPage
from odmf.webpage import lib

# Make autoreload
autoreload = 'noreload' not in sys.argv
print("autoreload =", autoreload)

print("Kill session lock files")
for fn in glob('webpage/sessions/*.lock'):
    os.remove(fn)

# Create the URL root object
root = Root()

# Create a heapy page to view memory usage
if 'heapy' in sys.argv:
    print("Load heapy")
    from guppy import hpy
    hp = hpy()
    hp.setrelheap()
    root.heapy = HeapyPage(hp)

#config="server.conf"

# Start the server
lib.start_server(root, autoreload=autoreload, port=conf.CFG_SERVER_PORT)
