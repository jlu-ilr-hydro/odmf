#!/usr/bin/env python

from odmf import odmf
import logging
import sys

if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logging.basicConfig(level='WARNING', stream=sys.stderr)
    odmf.cli()