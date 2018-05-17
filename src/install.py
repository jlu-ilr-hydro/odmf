from setuptools.command import easy_install

# install python packages
easy_install.main(
    ['genshi==0.7',
     'sqlalchemy==0.7.6',
     'psycopg2==2.4.5',
     'pytz==2015.07',
     'pandas==0.13.0.dev0',
     'bcrypt==0.4',
     'markdown==2.3.1',
     'matplotlib==1.3.1',
     'configparser==3.3.0.post2',
     'xlrd==0.9.4'])

# install linux software
# TODO: add linux software dep

# TODO: SETUP.PY script

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
#      [ #linux software
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
