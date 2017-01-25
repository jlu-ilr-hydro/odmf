from setuptools.command import easy_install

easy_install.main(
    ['genshi',
     'sqlalchemy',
     'psycopg2',
     'pytz',
     'pandas',
     'bcrypt',
     'markdown',
     'matplotlib',
     'configparser',
     'xlrd'])

# python --
#
#   genshi
#   sqlalchemy
#   psycopg2
#   pytz
#   pandas
#   bcrypt
#   markdown
#   matplotlib
#      [
#        python-tk
#        idle
#        python-pmw
#        python-imaging
#        python-qt5
#        libgtk2.0-dev
#      ]
#   configparser
#   xlrd
#
# linux --
#
#   postgresql-server-dev-X.Y
#   python-cherrypy
#   python-cherrypy3
