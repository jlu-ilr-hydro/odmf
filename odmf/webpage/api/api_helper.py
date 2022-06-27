import os
import inspect

def get_help(obj, url, append_to: dict = None):
    append_to = append_to or {}

    def is_api_or_method(obj):
        return inspect.ismethod(obj) or isinstance(obj, BaseAPI) and hasattr(obj, 'exposed')

    if inspect.ismethod(obj):
        append_to[url] = url.split('/')[-1] + str(inspect.signature(obj)) + ': ' + str(inspect.getdoc(obj))
    else:
        append_to[url] = inspect.getdoc(obj)
    for name, member in inspect.getmembers(obj, is_api_or_method):
        if not name.startswith('_'):
            append_to = get_help(member, '/'.join([url, name]), append_to)
    return append_to


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
