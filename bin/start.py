#!/usr/bin/env python

from odmf import odmf
import logging
import sys

if __name__ == '__main__':
    import coloredlogs, logging

    # By default the install() function installs a handler on the root logger,
    # this means that log messages from your code and log messages from the
    # libraries that you use will all show up on the terminal.
    coloredlogs.install(level='INFO')
    logger = logging.getLogger(__name__)

    # logging.basicConfig(level='INFO', stream=sys.stderr)
    odmf.cli()