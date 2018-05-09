#!/usr/bin/env python3

# Updates the transformed timeseries values due to migration reasons
#

# Purpose of this script
#
# 1. Delete already existing temporary records of transformed timeseries
#
# 2. Create records in the record-table from transformed timeseries datasets
#  and from recent values, which the transformation is applied on

import psycopg2
import conf

import numpy as np

import logging as _log

from collections import defaultdict
import time

def log(msg):
    t0 = time.strftime("%c")
    print("[LOG] {}: {}".format(t0, msg))


_log.basicConfig(level=_log.INFO)
_log.info('Start')


def transform(record, transformation):
    # value = 3
    result = eval(transformation, {'x': record[3]}, np.__dict__)
    if not type(result).__name__ == 'float':
        if type(result).__name__ == 'ndarray':
            result = result.flatten()[0]
        if type(result).__name__ in ['complex128', 'complex']:
            # return the real part of a complex number
            result = result.real
    return result


# Stepwise
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

connection = psycopg2.connect(database="schwingbach2", user=conf.CFG_DATABASE_USERNAME, password=conf.CFG_DATABASE_PASSWORD,
                 host=conf.CFG_DATABASE_HOST)
cur = connection.cursor()

cur.execute("SELECT * FROM record WHERE dataset in (SELECT DISTINCT id FROM transformed_timeseries)")

# all transformed timeseries that may be already hold records in the record table for deletion
all_possible_transformed_timeseries = cur.fetchall()

tt_size = len(all_possible_transformed_timeseries)
print("Found {} transformed records in the records table for deletion.".format(tt_size))
if tt_size > 0:
    # Delete all transforms records
    print("Start deletion ...")
    try:
        transformed_records = cur.execute("DELETE FROM record WHERE dataset in (SELECT id FROM transformed_timeseries)")
        connection.commit()
    except RuntimeError as e:
        print(e)
        print("Error while deleting already existing transformed records. Database operations rolled back.")
        connection.rollback()
    finally:
        print("Deletion of {} records was successfull.".format(cur.rowcount))
        cur.close()

        # TODO: is this neccessary?

#
# Creating new transformed timeseries records
#
cur = connection.cursor()


# fetch all sources
# TODO: add target to source
cur.execute("""SELECT DISTINCT source FROM transformed_timeseries tt LEFT JOIN transforms t """\
                          + """ON tt.id = t.target""")
sources = cur.fetchall()
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

records = dict()

# fetch all affected source records (cache them locally)
s_size = len(sources)
n = 0
for source in sources:
    n += 1
    print("{}/{}".format(n, s_size), end='\r')
    cur.execute("SELECT * FROM record WHERE dataset = %s", (source))
    records[source[0]] = cur.fetchall()
print("{}/{} Download finished".format(n, s_size))

# then iterate over the sources and insert the transformation into the respective target into the record table
try:
    t_size = len(targets_only)
    j = 0
    for target in targets_only:
        j+=1
        ids = 0
        print("Target {} of {}".format(j, t_size))

        sources = transformations[target[0]]
#        sources = [_source]
        expression = target[1]
        #print("Targtet: ", target)
        #print("Sources: ", sources)
        #print("Expression: ", expression)
        s_size = len(sources)
        n = 0
        for source in sources:
            n+=1
            print("Source {} to Target {}\n".format(source, target)\
                  +"Source {}/{}\nSource length: {}".format(n, s_size, len(records[source])), end='\r')

            for rec in records[source]:

                transformed_value = transform(rec, expression)

                # TODO: execute_batch
                cur.execute("""INSERT INTO record VALUES (%(id)s, %(dataset)s, %(time)s, %(value)s, %(sample)s,"""\
                + """%(comment)s, %(is_error)s);""", {'id': ids, 'dataset': target[0], 'time': rec[2],\
                                                     'value': transformed_value, 'sample': rec[4], 'comment': rec[5],
                                                     'is_error': rec[6]})

                # inc ids
                ids += 1

                # TODO: bulk inserting?
    connection.commit()
except RuntimeError as e:
    print(e)
    print(target, source)
    connection.rollback()
    exit(1)

print("Everything went fine!")
connection.commit()
cur.close()