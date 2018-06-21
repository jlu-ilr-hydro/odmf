# Observatory Data Management Framework

This project provides a webinterface for managing scientific data measurement based on 
[cherrypy](https://github.com/cherrypy/cherrypy) and [postgres](https://www.postgresql.org/).

[![License][license-image]][license-link]
[![Build Status][build-image]][build-link]

[license-image]: https://img.shields.io/badge/license-MIT-blue.png
[license-link]: http://opensource.org/licenses/MIT
[build-image]: https://travis-ci.org/jlu-ilr-hydro/odmf.svg?branch=master
[build-link]: https://travis-ci.org/jlu-ilr-hydro/odmf

# Installation

    $ git clone https://github.com/jlu-ilr-hydro/odmf.git
    $ cd odmf
    $ pip install -r requirements.txt
    $ cd odmf
    $ cp conf-template.py conf.py

Change the config with the instructions from [conf.py](https://jlu-ilr-hydro.github.io/odmf/source/conf.py) wiki page.
When the configuration is edited to meet your requirements, start the server and browse to https://localhost:8080

    $ python3 start.py

[Visit the institiute homepage](http://www.uni-giessen.de/faculties/f09/institutes/ilr/hydro?set_language=en)

