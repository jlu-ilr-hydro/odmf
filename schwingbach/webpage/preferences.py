'''
Created on 25.09.2012

@author: philkraf
'''

from auth import expose_for,group,users
import lib as web
import json
import os.path as op
json_in = web.cherrypy.tools.json_in
class Preferences(object):
    exposed=True
    default={'map': dict(lat=50.5,lng=8.55,zoom=16,type='hybrid'),
      'site': 1,
     }
    types=dict(map=dict(lat=float,lng=float,zoom=int,type=str),
               site=int)
    def __init__(self):
        try:
            self.data = json.load(file(self.filename))
        except:
            self.data = Preferences.default
    @property
    def filename(self):
        if users.current:
            return web.abspath('preferences/' + users.current.name + '.json')
        else:
            return web.abspath('preferences/any.json')
    def __getitem__(self,item):
        return self.data.get(item)
    def __setitem__(self,item,value):
        self.data.update({item:value})
        self.save()
    def __contains__(self,item):
        return item in self.data
       
    def save(self):
        file(self.filename,'w').write(web.as_json(self.data))
        
    
    @expose_for()
    def index(self,item=''):
        web.setmime(web.mime.json)
        data=self.data
        if item in data:
            return web.as_json(self.data[item])
        else:
            return web.as_json(self.data)
    
    @expose_for()
    @json_in()
    def update(self):
        kwargs = web.cherrypy.request.json 
        item = kwargs.pop('item',None)
        print 'update/',item,kwargs
        if item:
            value=self.data.setdefault(item,{})
            if hasattr(value,'update'):
                self.data[item].update(kwargs)
            print self.data 
        else:
            self.data.update(kwargs)
            print self.data
        self.save()
        return self.index()

        
    