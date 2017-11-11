#!/usr/bin/env bash
#
# Excluding
#
# E501 Line too long, no line break
# E265 Block comment should start with '# '
# W291 Trailing whitespace

pep8 . --ignore=E501,E265,W291
