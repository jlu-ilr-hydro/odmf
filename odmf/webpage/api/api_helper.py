import os
import inspect


class BaseAPI:
    ...


def get_help(obj, url):
    """
    Describes the API with a dictionary of available methods at the url.

    Structure

    api/url:
        doc: Some documentation
        parameters:  # Allowed parameters
          x: int
          y: str
        http_methods: # Allowed http methods (
          - GET
          - POST

    :param obj: Object to map
    :param url: API-Url
    """

    def is_api_or_method(obj):
        return inspect.ismethod(obj) or isinstance(obj, BaseAPI) and hasattr(obj, 'exposed')

    def method_params(callable):
        if inspect.ismethod(callable):
            return {
                p.name: p.annotation.__name__
                for p in inspect.signature(callable).parameters.values()
                if p.name not in ['args', 'kwargs']
            }
        else:
            return None

    if inspect.ismethod(obj):
        callable = obj
    elif inspect.ismethod(getattr(obj, 'index', None)):
        callable = obj.index
    else:
        callable = None

    doc = inspect.getdoc(obj)

    try:
        http_methods = callable._cp_config['tools.allow.methods']
    except (AttributeError, KeyError):
        http_methods = []

    parameters = method_params(callable)
    children = dict(
        get_help(member, '/'.join([url, name]))
        for name, member in inspect.getmembers(obj, is_api_or_method)
        if not name.startswith('_') and not name.endswith('index')
    )

    return url.split('/')[-1], dict(doc=doc, http_methods=http_methods, parameters=parameters, children=children, url=url)


def write_to_file(dest, src):
    """
    Write data of src (file in) into location of dest (filename)

    :param dest:  filename on the server system
    :param src: file contents input buffer
    :return:
    """

    with open(os.open(dest, os.O_CREAT | os.O_WRONLY, 0o770), 'w') as fout:
        while True:
            data = src.read(8192)
            if not data:
                break
            fout.write(data)
