'''
Created on 21.05.2014

@author: kraft-p
'''
import sys
import os
import dataimport as di
from dataimport.textimport import TextImport, TextImportDescription
from tools import Path
import time
from datetime import datetime
if len(sys.argv)!=4:
    print "usage: climateimport.py [newfile.dat] [siteid] [archivefile.dat]"

# Get filename for import from cmdline
nowstr = lambda : datetime.now().strftime('%Y-%m-%d %H:%M')
path = Path(sys.argv[1])
logfile = file(Path(path.up())+'autoimport.log','a')
i=0
while not path.exists():
    time.sleep(60)
    i+=1
    if i>20:
        logfile.write(nowstr() + ' After 20 tries does ' + path.basename + ' not exist\n' )
        sys.exit(1)
# Get siteid from cmdline
siteid = int(sys.argv[2])

# Create a TextImport
ia = TextImport(path.absolute, 'philipp', siteid) 

# get the configuration of the text import adapter
config =  ia.descriptor
# get the datasets o which the imported data is appended
for col in config.columns:
    ia.datasets[col.column] = col.append

logfile.write(nowstr() + ' Start to import data from ' + path.basename + '\n')

# Do the import
ia.submit()
# put out data to stdout
fin = file(path.absolute)
fout = file(sys.argv[3],'a')
for i,line in enumerate(fin):
    if i<config.skiplines:
        continue
    else:
        fout.write(line)
fin.close()
fout.close()
# Kill data file
os.remove(path.absolute)
logfile.write(nowstr() + path.basename + ' imported, copied to %s and killed\n' % Path(sys.argv[3]).basename)
logfile.close()         