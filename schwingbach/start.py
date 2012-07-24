#!/usr/bin/env python
# -*- coding:utf-8 -*-
'''
Created on 12.02.2012

@author: philkraf
'''


from webpage import Root
from webpage import lib
import sys
autoreload= not 'noreload' in sys.argv
print "autoreload =",autoreload
import db
db.Dataset.metadata.create_all(db.engine)
session=db.Session()
p=db.Person()              
users={'admin':'SB0:VK1'}
for p in session.query(db.Person):
    if p.telephone:
        pw = p.telephone.split()[-1]
    else:
        pw='VB1:SB0'
    users[p.username]=pw
session.close()
digest = {'tools.digest_auth.on': True,
          'tools.digest_auth.realm':'ilr',
          'tools.digest_auth.users':users,
                    }
lib.config['/user']=digest
lib.config['/site']=digest
lib.config['/site/kml']={'tools.digest_auth.on': False}
lib.config['/valuetype']=digest
lib.config['/download']=digest
lib.config['/dataset']=digest
lib.config['/job']=digest
lib.config['/log']=digest




lib.start_server(Root(), autoreload=autoreload, port=8081)