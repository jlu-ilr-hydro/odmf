'''
Created on 21.05.2014

@author: kraft-p
'''
import sys
import os

if not sys.version_info >= (3,5):
    raise Exception("This script is for Python 3 usage only. Please use \"python3\" instead of \"python\" to execute this script.")

# Fixes db error
# TODO: Find a consistent import process (ff)
from webpage import auth

from dataimport.textimport import TextImport
from tools import Path
import time
from datetime import datetime
from traceback import format_exc as traceback


def log(msg, stream=sys.stdout):
    stream.write(nowstr() + ' ' + msg + '\n')
    stream.flush()


if len(sys.argv) != 4:
    print("usage: climateimport.py [newfile.dat] [siteid] [archivefile.dat]")

# Get filename for import from cmdline


def nowstr():
    return datetime.now().strftime('%Y-%m-%d %H:%M')

path = Path(sys.argv[1])
i = 0
log('Wait for ' + path.absolute)
while not path.exists():
    time.sleep(60)
    i += 1
    if i > 20:
        log('After 20 tries does ' + path.basename + ' not exist', sys.stderr)
        sys.exit(1)
try:

    # Get siteid from cmdline
    siteid = int(sys.argv[2])
    log('Process settings for ' + path.basename)

    # Create a TextImport
    ia = TextImport(path.absolute, 'philipp', siteid)

    # get the configuration of the text import adapter
    config = ia.descriptor
    # get the datasets o which the imported data is appended
    for col in config.columns:
        ia.datasets[col.column] = col.append

    log('Start to import data from ' + path.basename)

    # Do the import
    ia.submit()
    # put out data to stdout
    fin = open(path.absolute)
    fout = open(sys.argv[3], 'a')
    for i, line in enumerate(fin):
        if i < config.skiplines:
            continue
        else:
            fout.write(line)
    fin.close()
    fout.close()
    # Kill data file
    os.remove(path.absolute)
    log(path.basename + ' imported, copied to %s and killed' %
        Path(sys.argv[3]).basename)
except:
    log(traceback(), sys.stderr)
