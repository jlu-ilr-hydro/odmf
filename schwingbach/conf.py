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

CFG_DATABASE_NAME = 'schwingbach'
CFG_DATABASE_USERNAME = 'schwingbach-user'
CFG_DATABASE_PASSWORD = 'VK1:SB0'
CFG_DATABASE_HOST = 'fb09-pasig.umwelt.uni-giessen.de'

#
# Media
#

# Relative path for storing the media
CFG_MEDIA_IMAGE_PATH = 'webpage/media'

# Map

CFG_MAP_DEFAULT = {
    'lat': 50.500030709695544,
    'lng': 8.55060081481929,
    'type': 'hybrid',
    'zoom': 17
}
