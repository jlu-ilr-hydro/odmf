#!/usr/bin/env python
# -*- coding:utf-8 -*-
'''
Created on 12.02.2012

@author: philkraf
'''


from webpage import Root, HeapyPage
from webpage import lib
import sys
autoreload= not 'noreload' in sys.argv
print "autoreload =",autoreload

root=Root()

if 'heapy' in sys.argv:
    print "Load heapy"
    from guppy import hpy
    hp=hpy()
    hp.setrelheap()
    root.heapy = HeapyPage(hp)
lib.start_server(root, autoreload=autoreload, port=8081)
