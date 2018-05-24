#!/usr/bin/env python3

# Updates the transformed timeseries values due to migration reasons
#

# Purpose of this script
#
# 1. Delete already existing temporary records of transformed timeseries
#
# 2. Create records in the record-table from transformed timeseries datasets
#  and from recent values, which the transformation is then applied on

import psycopg2
import psycopg2.extras
import conf

import numpy as np

import logging

from collections import defaultdict
import time
import datetime

# Logger configuration
_log = logging.getLogger('update_tranformedvalues')
_log.setLevel(logging.INFO)

fh = logging.FileHandler('update.log')
fh.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

# add handler
_log.addHandler(fh)
_log.addHandler(ch)


t0 = datetime.datetime.now()

_log.info('Start routine')


def transform(record, transformation):
    # value = 3
    result = eval(transformation, {'x': record[3]}, np.__dict__)

    # type saftey due to np mapping
    if not type(result).__name__ == 'float':
        if type(result).__name__ == 'ndarray':
            result = result.flatten()[0]
        if type(result).__name__ in ['complex128', 'complex']:
            # return the real part of a complex number
            result = result.real
    return result


# Stepwise algorithm
#
# 1. Delete all records which have ids of transformed timeseries (and so shouldn't exists by definition of the
#    schwingbach database schema)
#
# 2. Create all records of all transformed timeseries datasets.
#    For this
#    1. Get all source datasets
#    2. Get all target datasets
#    3. Get all source records
#    4. Compute target transformation (target-wise)
#
#       target = transformation(source_record, source_dataset)


connection = psycopg2.connect(database=conf.CFG_DATABASE_NAME, user=conf.CFG_DATABASE_USERNAME, password=conf.CFG_DATABASE_PASSWORD,
                 host=conf.CFG_DATABASE_HOST)
cur = connection.cursor()


# all transformed timeseries that may be already hold records in the record table for deletion
cur.execute("SELECT * FROM record WHERE dataset in (SELECT DISTINCT id FROM transformed_timeseries)")
all_possible_transformed_timeseries = cur.fetchall()

# If records are present, delete them
tt_size = len(all_possible_transformed_timeseries)
_log.info("Found {} transformed records in the records table for deletion.".format(tt_size))
if tt_size > 0:

    print("Start deletion ...")
    try:
        transformed_records = cur.execute("DELETE FROM record WHERE dataset in (SELECT id FROM transformed_timeseries)")
        connection.commit()
    except RuntimeError as e:
        print(e)
        _log.error("Error while deleting already existing transformed records. Database operations rolled back.")
        connection.rollback()
        exit(1)
    finally:
        cur.close()

_log.info("Deletion of {} records was successfull.".format(cur.rowcount))


# Creating new transformed timeseries records
cur = connection.cursor()

# fetch all sources
cur.execute("""SELECT DISTINCT source FROM transformed_timeseries tt LEFT JOIN transforms t """\
                          + """ON tt.id = t.target""")
sources = cur.fetchall()
#TODO: add debugging console arguments (with explicit source and target ids etc)
#sources = [(_source,)]

cur.execute("""SELECT DISTINCT target, source, expression FROM transformed_timeseries tt LEFT JOIN transforms t """\
                          + """ON tt.id = t.target""")# WHERE target = %s AND source = %s""", (_target, _source))
targets = cur.fetchall()

cur.execute("""SELECT DISTINCT target, expression FROM transformed_timeseries tt LEFT JOIN transforms t """\
                          + """ON tt.id = t.target""")# WHERE target = %s AND source = %s""", (_target, _source))
targets_only = cur.fetchall()

cur.execute("""SELECT target, source FROM transforms""")
transformations = defaultdict(list)

# key: target
# value: source [list]
for e in cur.fetchall():
    transformations[e[0]].append(e[1])

# fetch all affected source records (cache them locally)
records = dict()
s_size = len(sources)
n = 0
for source in sources:
    n += 1
    print("{}/{}".format(n, s_size), end='\r')
    cur.execute("SELECT * FROM record WHERE dataset = %s", (source))
    records[source[0]] = cur.fetchall()
print("{}/{} Download finished".format(n, s_size))
_log.info("Downloaded {} sources".format(s_size))

# then iterate over the sources and insert the transformation into the respective target into the record table
try:

    t_size = len(targets_only)

    # Iterate all targets
    j = 0
    for target in targets_only:

        j += 1
        ids = 0
        print("Target {} of {}".format(j, t_size))

        sources = transformations[target[0]]
        # TODO: debugging arguments
        # sources = [_source]
        expression = target[1]

        # Iter all sources, related to the iterated target at the moment
        s_size = len(sources)
        n = 0
        for source in sources:

            n+=1
            print("Source {}/{}".format(n, s_size), end='\r')

            # Iter all source records cached locally and transform them
            arglist = []
            for rec in records[source]:

                transformed_value = transform(rec, expression)
                # appends parameters for batch execution
                arglist += [{'id': ids, 'dataset': target[0], 'time': rec[2], 'value': transformed_value, \
                             'sample': rec[4], 'comment': rec[5], 'is_error': rec[6]}]
                # inc ids
                ids += 1

            # TODO: how big arglist can become, for maximum performance?
            # Batch execution for performance improvement
            psycopg2.extras.execute_batch(cur, """INSERT INTO record VALUES (%(id)s, %(dataset)s, %(time)s, %(value)s, %(sample)s,"""
                          + """%(comment)s, %(is_error)s);""", arglist)
    connection.commit()

except Exception as e:
    print(e)
    print(target, source)
    _log.error('Error while inserting transformed rows. Rolling back operations and exiting!')
    connection.rollback()
    exit(1)

t1 = datetime.datetime.now()
_log.info("Last commit")
_log.info("Update of transformed series was successful. Took {} to complete".format(t1-t0))
cur.close()

# TODO: Add monitoring/debugging behaviour
