# Parse conf.py in the root directory and check for validity
#
# A more detailed explanation of a valid configuration can be found
#  in the documentation
#

_mandatory = ['CFG_SERVER_PORT']

def parseConf(conf):

    # filter private module members
    mandatory = [e for e in dir(conf) if not e.startswith('__')]

    for k in mandatory:
        v = getattr(conf, k)
        if v in [None, ''] and k in _mandatory:
            raise ValueError("The config attribute {} is missing a value, but is mandatory.".format(k))
    return True

