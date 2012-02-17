'''
Created on 30.01.2012

@author: philkraf
'''
import sqlite3
import lib
import sys

def ORM(tablename,classname=None,db=lib.dbpath,pk=None):
    con = sqlite3.connect(db)
    classname = classname if classname else tablename.title()
    cur = con.execute('select * from %s limit 1' % tablename)
    fields = [d[0] for d in cur.description]
    #print "import lib"
    #print "from lib import sql"
    print "class %s(lib.Base):" % classname
    print "    __tablename__= '%s'" % tablename
    for f in fields:
        PK = ",primary_key=True" if f==pk else ""
        print "    %s=sql.Column(sql.String%s)" % (f,PK)

if __name__=='__main__':
    tn = sys.argv[1]
    if len(sys.argv)>2:
        cn = sys.argv[2]
    else:
        cn=None
    ORM(tn,cn)
    
        