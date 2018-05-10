# Parse conf.py in the root directory and check for validity
#
# A more detailed explanation of a valid configuration can be found
#  in the documentation
#

_mandatory = ['CFG_SERVER_PORT', 'CFG_DATABASE_NAME', 'CFG_DATABASE_USERNAME', 'CFG_DATABASE_PASSWORD',
              'CFG_DATABASE_HOST']


def parseConf(conf):
    """
    Checks validity of the config with scanning the conf module members

    :param conf:
    """
    # filter private module members
    mandatory = [e for e in dir(conf) if not e.startswith('__')]

    for k in mandatory:
        v = getattr(conf, k)
        if v in [None, ''] and k in _mandatory:
            raise ValueError("The config attribute {} is missing a value, but is mandatory.".format(k))
