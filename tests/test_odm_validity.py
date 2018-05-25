#!/usr/bin/env python3
# Checks validity of the database elements
# which can only be estimated on runtime

import requests
import psycopg2

from context import conf

from pprint import pprint

connection = psycopg2.connect(database=conf.CFG_DATABASE_NAME, user=conf.CFG_DATABASE_USERNAME,
                              password=conf.CFG_DATABASE_PASSWORD, host=conf.CFG_DATABASE_HOST)

validity = True

with connection.cursor() as cursor:

    # checks for identical time ranges
    cursor.execute("""SELECT * FROM seriescatalog WHERE begindatetime = enddatetime;""")
    if cursor.rowcount > 0:
        validity = False
        # not valid
        # send mail
        print('Not Valid: There are series with begin = start')

    # checks for empty series
    cursor.execute("""SELECT * FROM seriescatalog WHERE valuecount = 0;""")

    if cursor.rowcount > 0:
        validity = False
        # not valid
        # send mail
        print('Not Valid: There are series with valuecount = 0')

    # checks for similar rowcounts
    cursor.execute("""SELECT DISTINCT(variableid) FROM seriescatalog""")
    catalog_count = cursor.rowcount

    cursor.execute("""SELECT * FROM variables""")

    if cursor.rowcount != catalog_count:
        validity = False
        print('Not Valid: There are differences in variables published in the catalog and accessible via variables')


    # checks for similar rowcounts
    cursor.execute("""SELECT DISTINCT(siteid) FROM seriescatalog""")
    catalog_count = cursor.rowcount

    cursor.execute("""SELECT * FROM sites""")

    if cursor.rowcount != catalog_count:
        validity = False
        print('Not Valid: There are differences in sites published in the catalog and accessible via sites')


if validity:
    print("CUAHSI WOF Data of database {} is valid".format(conf.CFG_DATABASE_NAME))
