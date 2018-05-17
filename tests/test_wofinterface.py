#!/usr/bin/env python3
# Tests wateroneflow interface with predefined xml data
#  checks only response code

import requests

from context import tools
from context import conf
from tools import mail

from lxml import etree
import logging

# TODO: Centralize logging
# Logger configuration
logger = logging.getLogger('test_wofinterface')
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler('tests.log')
fh.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

# add handler
logger.addHandler(fh)
logger.addHandler(ch)

# configuration
receivers = conf.CFG_WOFTESTER_RECEIVER_MAIL
sender = conf.CFG_WOFTESTER_SENDER_MAIL
endpoint_url = conf.CFG_CUAHSI_WSDL_ENDPOINT

success_msg = 'TEST_WOFINTERFACE successful'

# TODO: Make this as a unit-test

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
    # TODO: extend xml requests in the xml folder with boundary cases
    files = {'file': open('wateroneflow/xml/{}-request.xml'.format(method_name.lower()), 'rb')}

    r = requests.post(endpoint_url,
                      headers=headers,
                      files=files)
    logger.debug('%s returned %s', method_name, r.status_code)
    # TODO: implement additional methods for checking the xml response
    if r.status_code is not 200:
        # Response should be 200, if not generate error
        logger.error('%s returned %s', method_name, r.status_code)
        logger.debug('Content was \'%s\'', r.content[:30])
        return method_name, r

    # Return with no error
    return None


def if_errors_email(errors, to=receivers):

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

#    mail.EMail(sender, to, subject, msg).send()


def if_no_errors_insert_log(errors, msg=success_msg):

    # filter None
    errors = [e for e in errors if e is not None]

    if errors is []:
        logger.info(msg)


if __name__ == '__main__':

    all_errors = []

    # fetching the wsdl methods remotely is sufficient since the WSDL can't be provided, no methods can't be
    # called either
    methods = parse_wsdl()

    logger.debug('Requesting {} methods'.format(len(methods)))

    if methods is None:
        # Then the HydroServer isn't running
        mail.EMail(sender, receivers,
                   'Could not fetch wsdl methods',
                   'The WSDL file on {} could not be fetched. Please check your HydroServerLite'.format(endpoint_url))\
            .send()

    for name in methods:
        logger.debug('Request wtih {} ...'.format(name))
        all_errors += [do_request(method_name=name)]

    if_errors_email(all_errors, to=receivers)

    if_no_errors_insert_log(all_errors)

    logger.debug('DONE')