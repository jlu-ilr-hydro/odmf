import cherrypy

from .. import lib as web
from ..auth import group, expose_for
from ...config import conf
import os
from traceback import format_exc as traceback


class Wiki(object):
    exposed = True

    def name2path(self, name):
        return conf.abspath('datafiles/wiki/' + name + '.wiki')

    @expose_for()
    def external(self, *args):
        from glob import glob
        args = list(args)
        name = '.'.join(args)
        title = ' / '.join(arg.title() for arg in args)
        filename = self.name2path(name.lower())
        content = ''
        related = ''
        pages = sorted([os.path.basename(s)[:-5]
                        for s in glob(conf.abspath('datafiles/wiki/%s*.wiki' % name.split('.')[0]))])
        if name in pages:
            pages.remove(name)
        if os.path.exists(filename):
            content = str(open(filename).read())
        elif args:
            if pages:
                content += '\n\n!!! box "Note:"\n    You can write an introduction to this topic with the edit button above.\n'
            else:
                content = '''
                           ## No content on %s

                           !!! box "This page is empty. Please write some meaningful content with the edit button."

                           To get some nice formatting, get wiki:help.
                           ''' % (title)
                content = '\n'.join(l.strip() for l in content.split('\n'))
        else:
            name = 'content'
        res = web.render('wiki_external.html', name=name, error='', wikitext=content, pages=pages).render('html',
                                                                                                          doctype='html')
        return res

    @expose_for()
    def default(self, *args):
        from glob import glob
        args = list(args)
        name = '.'.join(args)
        title = ' / '.join(arg.title() for arg in args)
        filename = self.name2path(name.lower())
        content = ''
        related = ''
        pages = sorted([os.path.basename(s)[:-5]
                        for s in glob(conf.abspath('datafiles/wiki/%s*.wiki' % name.split('.')[0]))])
        if name in pages:
            pages.remove(name)
        if os.path.exists(filename):
            content = str(open(filename).read())
        elif args:
            if pages:
                content += '\n\n!!! box "Note:"\n    You can write an introduction to this topic with the edit button above.\n'
            else:
                content = '''
                ## No content on %s

                !!! box "This page is empty. Please write some meaningful content with the edit button."

                To get some nice formatting, get wiki:help.
                ''' % (title)
                content = '\n'.join(l.strip() for l in content.split('\n'))
        else:
            name = 'content'
        res = web.render('wiki.html', name=name, error='',
                         wikitext=content, pages=pages).render('html', doctype='html')
        return res

    @expose_for(group.editor)
    def save(self, name, newtext):
        try:
            fn = self.name2path(name)
            open(fn, 'w').write(newtext)
        except:
            return 'err:' + traceback()

    @expose_for(group.admin)
    def delete(self, name):
        try:
            os.remove(self.name2path(name))
        except:
            return 'err:' + traceback()
        return ''
