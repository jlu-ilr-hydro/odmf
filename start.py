'''
Created on 12.02.2012

@author: philkraf
'''


from webpage import Root
from webpage import lib
import sys
autoreload= not 'noreload' in sys.argv
lib.start_server(Root(), autoreload=autoreload, port=8081)
