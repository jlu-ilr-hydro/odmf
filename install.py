from setuptools.command import easy_install

package_list = ['pandas', #
                'xlrd', # excel computing
                'genshi', # html template (trac)
                'config_parser',
                'psycopg2',
                'sqlalchemy']

easy_install.main( package_list )