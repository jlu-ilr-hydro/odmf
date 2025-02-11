"""
Tools to and from convert strings to numerous types
"""

import json
from datetime import datetime


def jsonhandler(obj):
    if hasattr(obj, '__jdict__'):
        return obj.__jdict__()
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        return obj.__dict__


def as_json(*args, **kwargs) -> str:
    """
    Builds a JSON string representation of the given object using __jdict__ methods
    of the objects or of owned objects
    Parameters
    ----------
    obj
        The object to stringify

    Returns
    -------
    A JSON string
    """
    if len(args) == 1:
        return json.dumps(args[0], indent=4, default=jsonhandler)
    elif len(args) == 0:
        return json.dumps(kwargs, indent=4, default=jsonhandler)
    elif kwargs:
        raise ValueError('You can\'t create a json representation from mixing positional and key word arguments')
    else:
        return json.dumps(list(args), indent=4, default=jsonhandler)


def formatdate(t=None, fmt='%d.%m.%Y'):
    if not t:
        return datetime.today().strftime(fmt)
    try:
        return t.strftime(fmt)
    except (TypeError, ValueError):
        return None


def formattime(t, showseconds=True):
    try:
        return t.strftime('%H:%M:%S' if showseconds else '%H:%M')
    except (TypeError, ValueError):
        return None


def formatdatetime(t=None, fmt='%d.%m.%Y %H:%M:%S'):
    if not t:
        t = datetime.now()
    try:
        return t.strftime(fmt)
    except (TypeError, ValueError):
        return None


def formatfloat(v, style='%g'):
    try:
        return style % v
    except (TypeError, ValueError):
        return 'N/A'


def parsedate(s, raiseerror=True):
    from dateutil.parser import parse, isoparse
    if not s:
        return None
    # res = None
    try:
        return isoparse(s)
    except ValueError:
        ...
    try:
        return parse(s, dayfirst=True)
    except ValueError:
        if raiseerror:
            raise ValueError(f'{s} is not a valid date')
        else:
            return None


def conv(cls, s, default=None):
    """
    Convert string s to class cls
    Parameters
    ----------
    cls
        A class to convert to (eg. float, int, datetime)
    s
        A string to convert
    default
        A default answer, if the conversion fails. Else return None

    Returns
    -------
    cls(s)

    """
    if cls is datetime:
        return parsedate(s)
    try:
        return cls(s)
    except (TypeError, ValueError):
        return default


def to_list(param, cls=None)->list:
    """
    Web parameters in this form abc[] contain a string if they have single parameter
    or a list of strings if they have multiple parameters. This function ensures
    a list.

    :param param:
    :param cls:  If a class is given, the content is converted to that class
    :return: List[cls|str]
    """
    if not param:
        return []
    if type(param) is str: param=[param]
    if cls is None:
        return param
    else:
        return [conv(cls, p) for p in param]


