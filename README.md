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

## Installation in a virtual environment for test and development

While the docker installation in preferred, odmf can be installed in a python virtual environment for testing purposes

### Make a virtual environment

Install virtual environment in directory `venv` and upgrade infrastructure, and activate it

Linux / MacOS:

    $ python -m venv venv
    $ source venv/bin/activate
    $ python -m pip install --upgrade pip wheel setuptools

Windows needs an extra python installation, you might need to put it on your PATH. Then do from a PowerShell
terminal:

    PS C:\ODMF> python -m venv venv
    PS C:\ODMF> .\venv\Scripts\activate
    PS C:\ODMF> python -m pip install --upgrade pip wheel setuptools


### Install odmf directly from github (for testing)
Install odmf (this will take sometime and install many requirements),

    $ pip install https://github.com/jlu-ilr-hydro/odmf/archive/master.zip

### or download the odmf source and install your local version (for development)

    $ git clone https://github.com/jlu-ilr-hydro/odmf odmf-src
    $ pip install -e odmf-src/
    
Check the command line tool

    $ odmf --help

## Configure ODMF

Create a folder for your instance, go there as your work dir and create a configuration file with

    $ odmf configure

Edit the configuration file config.yaml for your needs, eg set the right db connection. If you are
fine to use SQLite (ok if you have only very few parallel connections, not for production), you can leave
the db connection as is. Enter a valid Google-Maps-API key, configure your http-port. If everything is settled, create the base db structure with

    $ odmf db-create

## Start ODMF

Now you are ready to go:

    $ odmf start -b

Starts ODMF in your commandline and opens a webbrowser with the page. Note: ODMF stops if you close the command line. If you want to run ODMF as a service, either study how to start a service on your OS or just use docker.

You can interact with the database in a prepared IPython terminal:

    $ odmf interactive