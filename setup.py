from setuptools import setup, find_packages
import sys
with open('requirements.txt') as req:
    requirements = req.read()

    if sys.platform == 'win32':
        requirements = requirements.replace('psycopg2', 'psycopg2-binary')
    requirements = requirements.splitlines()
print('\n'.join(requirements))
setup(name='odmf',
      version='1.0',
      description='Observatory Data Management Framework',
      author='Philipp Kraft',
      author_email='philipp.kraft@umwelt.uni-giessen.de',
      url='https://github.com/jlu-ilr-hydro/odmf',
      packages=find_packages(),
      install_requires=requirements,
      entry_points='''
        [console_scripts]
        odmf=odmf.tools.cli:cli
      '''
      )
