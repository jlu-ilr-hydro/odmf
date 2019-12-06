import cherrypy

from .. import lib as web
from ...config import conf
from ..auth import users, group, expose_for
from ..upload import write_to_file

import os
from traceback import format_exc as traceback

@web.show_in_nav_for(4)
class AdminPage(object):
    """
    Displays forms and utilites for runtime configuration of the application, which will be made persistent
    """

    @expose_for(group.admin)
    def default(self, error='', success=''):

        return web.render('admin.html', error=error, success=success, MEDIA_PATH={
            'logo': conf.nav_left_logo,
            'banner-left': conf.nav_background
        }).render()

    @expose_for(group.admin)
    def upload(self, imgtype, imgfile, **kwargs):

        runtimedir = os.path.realpath('.') + '/'

        fn = runtimedir + 'webpage'

        def _save_to_location(location, file):
            """
            Helper function
            """
            error = ''

            if not os.path.isfile(location):
                cherrypy.log.error('No image present at \'%s\'. Creating it now!')

            try:
                write_to_file(location, imgfile.file)
            except:
                error += '\n' + traceback()
                print(error)

            return error

        # check for image types to determine location
        if imgtype == 'logo':
            # save to logo location
            error = _save_to_location(fn + conf.nav_left_logo, imgfile)

        elif imgtype == 'leftbanner':
            # save to leftbanner location
            error = _save_to_location(fn + conf.nav_background, imgfile)

        else:
            cherrypy.log.error('Adminpage form value imgtype is wrong')
            cherrypy.response.status = 400
            raise cherrypy.HTTPError(status=400, message='Bad Request')

        if error is '':
            msg = 'Successfully uploaded image. Reload page to view results'
            raise web.HTTPRedirect('/admin?success=%s' % msg)
        else:
            raise web.HTTPRedirect('/admin/?error=%s' % error)
