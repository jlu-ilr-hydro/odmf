"""
This moudle provides the default configuration for the homepage
It holds the data that differs from several database application and has to
be changed every time a new application is set up
"""

#
# Date/Time and Timezones
#

# Note: Has to be in pytz format
CFG_DATETIME_DEFAULT_TIMEZONE = 'Europe/Berlin'

#
# Database
#

# sqlite | postgres
DATABASE='sqlite'
SQLITE_PATH = 'data.sqlite'

#
# Media
#

# Relative path for storing the media
CFG_MEDIA_IMAGE_PATH = 'webpage/media'
# TODO: refactor this in the whole project
DATAFILES_PATH = 'webpage/datafiles'

# Pattern for the relative path storing manual measurements files and there and the subfolders their have special
# treatments from dataimport/mm.py
CFG_MANUAL_MEASUREMENTS_PATTERN = '(.+\/)*datafiles\/lab\/([a-zA-Z0-9]+\/)*.*\.(xls|xlsx)$'

# Map
# atm the schwingbach valley location is zoomed in
CFG_MAP_DEFAULT = {
    'lat': 55.550330709695544,
    'lng': 12.55060081481929,
    'type': 'hybrid',
    'zoom': 17
}

#
# Upload
#
CFG_UPLOAD_MAX_SIZE = 25000000  # 25 mb

CFG_SERVER_PORT=8081

#
# CUAHSI / WaterOneFlow
#

# Sets the value of a base directive of a head tag.
# This is necessary due to special server configuration
#HEAD_BASE = 'https://fb09.pasig.umwelt.uni-giessen.de/schwingbach'
HEAD_BASE = ''
