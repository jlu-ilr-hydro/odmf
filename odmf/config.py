# Parse conf.py in the root directory and check for validity
#
# A more detailed explanation of a valid configuration can be found
#  in the documentation
#

import yaml
from pathlib import Path
import sys
from logging import warning

class ConfigurationError(RuntimeError):
    pass


class Configuration:
    """
    The configuration class. Change the configuration by providing a config.yml in the home directory

    Mandatory fields are defined as (...), optional as None or with a default value
    """
    datetime_default_timezone = 'Europe/Berlin'
    database_type = 'postgres'
    database_name = ...
    database_username = ...
    database_password = ...
    database_host = '127.0.0.1'

    static = 'static'
    media_image_path = 'webpage/media'
    nav_background = '/media/gladbacherhof.jpg'
    nav_left_logo = '/media/lfe-logo.png'
    manual_measurements_pattern = '(.+\\/)*datafiles\\/lab\\/([a-zA-Z0-9]+\\/)*.*\\.(xls|xlsx)$'
    map_default = {'lat': 50.5, 'lng': 8.55, 'type': 'hybrid', 'zoom': 15}
    upload_max_size = 25000000
    server_port = ...
    woftester_receiver_mail = ['philipp.kraft@umwelt.uni-giessen.de']
    woftester_sender_mail = 'woftester@umwelt.uni-giessen.de'
    cuahsi_wsdl_endpoint = 'http://fb09-pasig.umwelt.uni-giessen.de/wof/index.php/cuahsi_1_1.asmx?WSDL'
    smtp_serverurl = 'mailout.uni-giessen.de'
    head_base = ''

    def __bool__(self):
        return ... not in vars(self).values()

    def update(self, conf_dict: dict):

        unknown_keys = []
        for k in conf_dict:
            if hasattr(self, k):
                setattr(self, k, conf_dict[k])
            else:
                unknown_keys.append(k)
        if unknown_keys:
            raise ConfigurationError(f'Your configuration contains unknown keys: {",".join(unknown_keys)}')

        return self

    def __init__(self, **kwargs):

        vars(self).update({
            k: v
            for k, v in vars(type(self)).items()
            if not k.startswith('_') and not callable(v)
        })

        self.update(kwargs)

    def to_yaml(self, stream=sys.stdout):
        """
        Exports the current configuration to a yaml file
        :param stream: A stream to write to
        """
        d = {
            k: v
            for k, v in vars(self).items()
            if not callable(v) and not k.startswith('_')
        }
        yaml.safe_dump(d, stream)


def load_config():
    conf_file = Path('.') / 'config.yml'
    if not conf_file.exists():
        warning(f'{conf_file.absolute().as_posix()} '
                   f'not found. Create a template with "odmf configure". Using incomplete configuration')
        conf_dict = {}
    else:
        conf_dict = yaml.safe_load(conf_file.open())
    return Configuration(**conf_dict)


def import_module_configuration(conf_module_filename):
    """
    Migration utitlity to create a conf.yaml from the old ODMF 0.x conf.py module configuration

    :param conf_module_filename: The conf.py configuration file
    """
    code = compile(open(conf_module_filename).read(), 'conf.py', 'exec')
    config = {}
    exec(code, config)

    def c(s: str):
        return s.replace('CFG_', '').lower()

    config = {
        c(k): v
        for k, v in config.items()
        if k.upper() == k and k[0] != '_' and not callable(v)
    }

    config['database_type'] = config.pop('database', 'postgres')

    conf = Configuration(**config)

    return conf


conf = load_config()
