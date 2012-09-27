'''
Created on 25.09.2012

@author: philkraf
'''

from auth import expose_for,group,users
import lib as web
import json
import os.path as op

class Preferences(object):
    default={'map': dict(lat=50.5,lng=8.55,zoom=16,type='hybrid'),
      'site': 1,
     }
    @property
    def filename(self):
        if users.current:
            return web.abspath('preferences/' + users.current.name + '.json')
        else:
            return web.abspath('preferences/any.json')
    @property
    def data(self):
        session = web.cherrypy.session
        if 'preferences' in session:
            return session['preferences']
        elif users.current and op.exists(self.filename):
            session['preferences'] = json.load(file(self.filename))
        else:
            session['preferences'] = Preferences.default
        return session['preferences']
    
        
    def save(self):
        f = file(self.filename,'w')
        json.dump(self.data,f,indent=4)
    
    @expose_for(group.logger)
    def index(self):
        web.setmime(web.mime.json)
        return json.dumps(self.data,indent=4)
    
    @expose_for(group.logger)
    def update(self,item=None):
        print 'update/',item
        cl = web.cherrypy.request.headers['Content-Length']
        rawbody = web.cherrypy.request.body.read(int(cl))
        kwargs = json.loads(rawbody)
        if item:
            value=self.data.setdefault(item,{})
            if hasattr(value,'update'):
                value.update(kwargs)
            print value 
                
        else:
            self.data.update(kwargs)
            print self.data
        self.save()
        return self.index()

        
    