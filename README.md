# Observatory Data Management Framework

![GitHub release (latest by date)](https://img.shields.io/github/v/release/jlu-ilr-hydro/odmf)

### This project provides a webinterface for managing scientific data measurement based on

[cherrypy](https://github.com/cherrypy/cherrypy) and [postgres](https://www.postgresql.org/).

[![License][license-image]][license-link]

[license-image]: https://img.shields.io/badge/license-MIT-blue.png
[license-link]: http://opensource.org/licenses/MIT


For further information please visit the [documenation](https://jlu-ilr-hydro.github.io/odmf).

# Installation

## Recommended installation in a docker-container

Go to the [odmf-docker ![GitHub top language](https://img.shields.io/github/languages/top/jlu-ilr-hydro/odmf-docker)](https://github.com/jlu-ilr-hydro/odmf-docker) repository and follow the instructions there.

## Installation in a virtual environment

While the docker installation in preferred, odmf can be installed in a python virtual environment for testing purposes

Install virtual environment in directory `venv` and upgrade infrastructure, and activate it

    $ python3.9 -m venv venv
    $ source venv/bin/activate
    $ python -m pip install --upgrade pip wheel setuptools

Install odmf from here 

    $ pip install https://github.com/jlu-ilr-hydro/odmf/archive/master.zip
    
Check command line tool

    $ odmf --help


    $ pip install -e odmf-src
    $ odmf --help
    $ 

Change the config with the instructions from [conf.py](https://jlu-ilr-hydro.github.io/odmf/source/conf.py) wiki page.
When the configuration is edited to meet your requirements, start the server and browse to https://localhost:8080

    $ python3 start.py

[Visit the institute's homepage](http://www.uni-giessen.de/faculties/f09/institutes/ilr/hydro?set_language=en)
