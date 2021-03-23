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


def get_version(rel_path):
    import os

    def read(rel_path):
        here = os.path.abspath(os.path.dirname(__file__))
        with open(os.path.join(here, rel_path)) as f:
            return f.read()
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


setup(name='odmf',
      version=get_version('odmf/__init__.py'),
      description='Observatory Data Management Framework',
      author='Philipp Kraft',
      author_email='philipp.kraft@umwelt.uni-giessen.de',
      url='https://github.com/jlu-ilr-hydro/odmf',
      packages=find_packages(),
      python_requires='>=3.8',
      install_requires=get_requirements(),
      include_package_data=True,

      entry_points='''
        [console_scripts]
        odmf=odmf.odmf:cli
      '''
      )
