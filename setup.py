from setuptools import setup, find_packages
import sys
import os


def get_requirements():
    """Reads the actual requirements from requirements.txt"""
    with open('requirements.txt') as req:
        requirements = req.read()

        if sys.platform == 'win32':
            requirements = requirements.replace('psycopg2', 'psycopg2-binary')
        return requirements.splitlines()


def get_datafiles(from_dir):
    return [
        (os.path.normpath(d), [
            os.path.join(d, f) for f in files
        ])
        for d, dirs, files in os.walk(from_dir)
        if files
    ]


setup(name='odmf',
      version='1.0',
      description='Observatory Data Management Framework',
      author='Philipp Kraft',
      author_email='philipp.kraft@umwelt.uni-giessen.de',
      url='https://github.com/jlu-ilr-hydro/odmf',
      packages=find_packages(),
      python_requires='>=3.6',
      install_requires=get_requirements(),
      data_files=get_datafiles('odmf.static'),
      entry_points='''
        [console_scripts]
        odmf=odmf.odmf:cli
      '''
      )
