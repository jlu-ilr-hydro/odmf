#!/usr/bin/env python

from odmf import odmf
import logging
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    odmf.cli()