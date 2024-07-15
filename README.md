# Observatory Data Management Framework

![GitHub release (latest by date)](https://img.shields.io/github/v/release/jlu-ilr-hydro/odmf)
![Github actions](https://github.com/jlu-ilr-hydro/odmf/actions/workflows/python-app.yml/badge.svg)
### This project provides a webinterface for managing scientific data measurement based on
[cherrypy](https://github.com/cherrypy/cherrypy) and [postgres](https://www.postgresql.org/).

[![License][license-image]][license-link]

[license-image]: https://img.shields.io/badge/license-MIT-blue.png
[license-link]: http://opensource.org/licenses/MIT


The concept was presented as a poster at the EGU GA 2017 (Vienna) by Kraft et al 
[![DOI](https://img.shields.io/badge/doi-10.13140%2FRG.2.2.32891.54563-blue)](https://doi.org/10.13140/RG.2.2.32891.54563)

# Installation

## Recommended installation in a docker-container

Go to the [odmf-docker ![GitHub top language](https://img.shields.io/github/languages/top/jlu-ilr-hydro/odmf-docker)](https://github.com/jlu-ilr-hydro/odmf-docker) repository and follow the instructions there.

## Installation in a virtual environment

While the docker installation in preferred, odmf can be installed in a python virtual environment for testing purposes

Install virtual environment in directory `venv` and upgrade infrastructure, and activate it

    $ python -m venv venv
    $ source venv/bin/activate
    $ python -m pip install --upgrade pip wheel setuptools

Install odmf from here 

    $ pip install https://github.com/jlu-ilr-hydro/odmf/archive/master.zip
    
Check command line tool

    $ odmf --help


