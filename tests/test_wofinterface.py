#!/usr/bin/env python3
# Tests wateroneflow interface with predefined xml data
#  checks only response code

import requests

from context import tools
from context import conf
from tools import mail

from lxml import etree

receiver = conf.CFG_WOFTESTER_RECEIVER_MAIL
sender = conf.CFG_WOFTESTER_SENDER_MAIL
endpoint_url = conf.CFG_CUAHSI_WSDL_ENDPOINT


def parse_wsdl():
    """ Returns wsdl methods """
    # Determine wsdl service methods
    tree = etree.parse(endpoint_url)
    root = tree.getroot()

    # Node with explicit name has methods as childs
    #TODO: make this safe, with eg.g. iteration and string match, instead of fixed values
    portType = root[80]
    assert portType.attrib.get('name') == 'WaterOneFlow'

    # scrap methods from xml node
    return [ptype.attrib.get('name') for ptype in portType]


def do_request(method_name=None):

    # Set necessary headers
    headers = {'Content-Type': 'text/xml',
               'charset': 'utf-8',
               'SOAPAction': 'http://www.cuahsi.org/his/1.1/ws/{}'.format(method_name)}

    # Load SOAP xml request files
    files = {'file': open('wateroneflow/xml/{}-request.xml'.format(method_name.lower()), 'rb')}

    r = requests.post(endpoint_url,
                      headers=headers,
                      files=files)

    if r.status_code is not 200:
        # Response should be 200, if not generate error
        return method_name, r

    # Return with no error
    return None


def if_errors_email(errors, to=receiver):

    # filter None values
    errors = [e for e in errors if e is not None]

    # Prepare Mail contents and send
    subject = """WaterOneFlow Tester: {} of {} Methods failed""".format(len(errors), len(methods))
    msg = """{} of {} Methods failed to return a 200 response code\n\n""".format(len(errors), len(methods))
    for e in errors:
        msg += """Method {} has {} response code\n""".format(e[0], e[1].status_code)

    msg += "\n\n"
    msg += "Check your endpoint at {}".format(endpoint_url[:-30], endpoint_url[:-30])

    msg += "\nThis message is automatically generated."

    mail.EMail(sender, [receiver], subject, msg).send()


if __name__ == '__main__':

    all_errors = []

    # fetching the wsdl methods remotely is sufficient since the WSDL can't be provided, no methods can't be
    # called either
    methods = parse_wsdl()

    print('Requesting {} methods'.format(len(methods)))

    if methods is None:
        # Then the HydroServer isn't running
        mail.EMail(sender, [receiver],
                   'Could not fetch wsdl methods',
                   'The WSDL file on {} could not be fetched. Please check your HydroServerLite'.format(endpoint_url))\
            .send()

    for name in methods:
        print('Request wtih {} ...'.format(name), end='')
        all_errors += [do_request(method_name=name)]
        print('Done.')

    if_errors_email(all_errors, to=receiver)
