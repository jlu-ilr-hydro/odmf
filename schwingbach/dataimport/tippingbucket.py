'''
Created on 03.03.2013

@author: kraft-p
'''
from __future__ import division
import db
from datetime import datetime, timedelta
from collections import namedtuple
import sys
import os
from base import ImportAdapter, ImportStat
from traceback import format_exc as traceback

class TippingBucketImporter(ImportAdapter):
    def __init__(self):
        pass
    
    