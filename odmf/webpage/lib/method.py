"""
Decorator to allow / disallow HTML-Methods on exposed functions
"""
import cherrypy

post = cherrypy.tools.allow(methods=['POST'])
put = cherrypy.tools.allow(methods=['PUT'])
post_or_put = cherrypy.tools.allow(methods=['PUT', 'POST'])
post_or_delete = cherrypy.tools.allow(methods=['DELETE', 'POST'])
get = cherrypy.tools.allow(methods=['GET', 'HEAD'])
