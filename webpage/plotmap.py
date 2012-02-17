'''
Created on 10.02.2012

@author: philkraf
'''

import Image
import ImageDraw
import pylab
import numpy
import os
import projection
from cStringIO import StringIO
import lib

class ImageMap(object):
    def __init__(self,filename):
        fname,imgext = os.path.splitext(filename)
        worldext = imgext[:2] + imgext[-1] + 'w'
        worldname = fname + worldext
        if not os.path.exists(filename):
            raise IOError('Background map %s not found' % filename)
        elif not os.path.exists(worldname):
            raise IOError('Background map world file %s not found' % worldname)
        else:
            self.image=Image.open(filename)
            world=numpy.fromfile(worldname,sep='\n')
            self.upperleft = world[-2,-1]
            self.cellsize = world[0,3]
    def UTMtoImage(self,x,y):
        xy=numpy.array((x,y))
        image = int((xy-self.upperleft)/self.cellsize)
        return image[0],-image[1]
    def LLtoImage(self,lon,lat):
        z,x,y = projection.LLtoUTM(self.ellipsoid, lat, lon)
        return self.UTMtoImage(x, y)
                
        

class BackgroundMap:
    def __init__(self,filename):        
        fname,imgext = os.path.splitext(filename)
        worldext = imgext[:2] + imgext[-1] + 'w'
        worldname = fname + worldext
        if not os.path.exists(filename):
            raise IOError('Background map %s not found' % filename)
        elif not os.path.exists(worldname):
            raise IOError('Background map world file %s not found' % worldname)
        else:
            self.image=Image.open(filename)
            world=numpy.fromfile(worldname,sep='\n')
            left,top = world[-2:]
            bottom = top + world[3] * self.image.size[1]
            right = left + world[0] * self.image.size[0]
            self.extent = (left,right,bottom,top)
    
    origin = 'bottom'

    @lib.expose
    @lib.mimetype('image/png')
    def index(self,**kwargs):
        self.draw(**kwargs)
        outf = StringIO()
        pylab.savefig(outf,dpi=100.)
        return outf.getvalue()
    def draw(self,**kwargs):
        kwargs['extent']=self.extent
        kwargs['origin']='bottom'
        kwargs['aspect']='equal'
        fig=pylab.gcf()
        fig.set_size_inches(11.47,14.44)
        pylab.clf()
        pylab.imshow(self.image,**kwargs)
        pylab.axis('off')
        pylab.grid()
        pylab.subplots_adjust(0,0,1,1,0,0)

class Map(object):
    def __init__(self,backgroundfile):
        self.background = BackgroundMap(backgroundfile)
        self.ellipsoid = 23 # WGS-84
    @lib.expose
    @lib.mimetype('image/png')
    def index(self):
        return self.background.index()
    
    def draw(self,sites,style='ro',**kwargs):
        fig=pylab.gcf()
        pylab.clf()
        self.background.draw()
        x,y = pylab.transpose([projection.LLtoUTM(self.ellipsoid, s.lat, s.lon)[1:] for s in sites])
        pylab.plot(x,y,style)
        for s,px,py in zip(sites,x,y):
            pylab.text(px,py,s.name)
        fig.set_size_inches(11.47,14.44,forward=True)
        outf = StringIO()
        pylab.savefig(outf,dpi=100.)
        return outf.getvalue()

