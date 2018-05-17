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

CFG_DATABASE_NAME = ''
CFG_DATABASE_USERNAME = ''
CFG_DATABASE_PASSWORD = ''
CFG_DATABASE_HOST = ''

#
# Media
#

# Relative path for storing the media
CFG_MEDIA_IMAGE_PATH = 'webpage/media'

# Pattern for the relative path storing manual measurements files and there and the subfolders their have special
# treatments from dataimport/mm.py
CFG_MANUAL_MEASUREMENTS_PATTERN = '(.+\/)*datafiles\/lab\/([a-zA-Z0-9]+\/)*.*\.(xls|xlsx)$'

# Map
# atm the schwingbach valley location is zoomed in
CFG_MAP_DEFAULT = {
    'lat': 50.500030709695544,
    'lng': 8.55060081481929,
    'type': 'hybrid',
    'zoom': 17
}

#
# Upload
#
CFG_UPLOAD_MAX_SIZE = 25000000  # 25 mb

#
# CUAHSI / WaterOneFlow
#

CFG_WOFTESTER_RECEIVER_MAIL = ['']
CFG_WOFTESTER_SENDER_MAIL = ''
CFG_CUAHSI_WSDL_ENDPOINT = ''

SMTP_SERVERURL = ''

# TODO: Is this the right place?
CFG_SERVER_SSL = False
CFG_SERVER_EXPOSE_WOF_INTERFACE = True
CFG_SERVER_PORT = 8081

# Sets the value of a base directive of a head tag.
# This is necessary due to special server configuration
#HEAD_BASE = 'https://fb09.pasig.umwelt.uni-giessen.de/schwingbach'
HEAD_BASE = ''
