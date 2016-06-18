"""
Implementation of a mechanism to ensure the validity of the conf.py
"""
from re import search

import conf


def test_pattern():

    print "\t=> Test regex pattern"

    testdirs = ["/home/user/code/repo/datafiles/lab/test.xls",
    "/home/user/code/repo/datafiles/lab/subidr/test.xlsx",
    "datafiles/lab/test.xls",
    "datafiles/lab/subidr/test.xlsx"]

    hasError = False

    for dir in testdirs:
        if not search(conf.CFG_MANUAL_MEASUREMENTS_PATTERN, dir):
            hasError = True
            print "Error at %s adjust the testcases or the pattern" % dir

    return hasError

fns = [test_pattern]

hasError = False

print "Checking conf.py ..."

for f in fns:
    if f():
       hasError = True

if not hasError:
    print "Ok. conf.py is valid"