'''
Created on 25.09.2012

@author: philkraf
'''

from auth import expose_for,group,users
import lib as web
import json
import os.path as op
class Preferences(object):
    data={'map': dict(lat=50.5,lon=8.55,zoom=16,type='hybrid'),
          'site': 1,
         }
         

    def save(self):
        f = file(web.abspath('preferences/' + users.current.name),'w')
        json.dump(self.data,f,encoding='utf-8',indent=4)
    
    def update(self,**kwargs):
        self.data.update(kwargs)
    def updateitem(self,item,*args,**kwargs):
        value = self.data.setdefault(item,{})
        if hasattr(value,'update'):
            value.update(kwargs)
        elif args:
            value=args[0]                                                   
    
    def load(self):
        fn = web.abspath('preferences/' + self.data['user'] + '.json')
        if op.exists(fn):
            f = file(fn)
            newpref = json.load(f)
            self.update(newpref)
        
    