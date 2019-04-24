from setuptools import setup, find_packages

setup(name='ODMF',
      version='0.1',
      description='Observatory Data Management Framework',
      author='Philipp Kraft',
      author_email='philipp.kraft@umwelt.uni-giessen.de',
      url='https://github.com/jlu-ilr-hydro/odmf',
      packages=find_packages(),
      install_requires=[
          'sqlalchemy',
          'xlrd',
          'numpy',
          'pytz',
          'bcrypt',
          'matplotlib'
      ])
