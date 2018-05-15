#!/usr/bin/env python3
# Checks validity of the database elements
# which can only be estimated on runtime

import requests
import psycopg2

import conf

from pprint import pprint

connection = psycopg2.connect(database=conf.CFG_DATABASE_NAME, user=conf.CFG_DATABASE_USERNAME,
                              password=conf.CFG_DATABASE_PASSWORD, host=conf.CFG_DATABASE_HOST)

with connection.cursor() as cursor:

    # checks for identical time ranges
    cursor.execute("""SELECT * FROM seriescatalog WHERE begindatetime = enddatetime;""")
    if cursor.rowcount > 0:
        # not valid
        # send mail
        pprint(cursor.fetchall())
        print('Not Valid: There are series with begin = start')

    # checks for empty series
    cursor.execute("""SELECT * FROM seriescatalog WHERE valuecount = 0;""")
    if cursor.rowcount > 0:
        # not valid
        # send mail
        pprint(cursor.fetchall())
        print('Not Valid: There are series with valuecount = 0')

print("CUAHSI WOF Data of database {} is valid".format(conf.CFG_DATABASE_NAME))
