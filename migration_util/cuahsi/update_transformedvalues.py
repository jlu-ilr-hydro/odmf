#!/usr/bin/env python3

# Updates the transformed timeseries values due to migration reasons
#

# Purpose of this script
#
# 1. Delete already existing temporary records of transformed timeseries
#
# 2. Create records in the record-table from transformed timeseries datasets
#  and from recent values, which the transformation is applied on

import webpage.auth
import db
import sys

import psycopg2
import conf

import logging as _log

import time

from create_transforms import delete_transforms_for, create_transforms_for

def log(msg):
    t0 = time.strftime("%c")
    print("[LOG] {}: {}".format(t0, msg))


_log.basicConfig(level=_log.INFO)
_log.info('Start')

def transform(record, transformation):
    # TODO: transfomation
    return record

with psycopg2.connect(database="schwingbach2", user=conf.CFG_DATABASE_USER, password=conf.CFG_DATABASE_PASSWORD,
                     host=conf.CFG_DATABASE_HOST) as connection:
    cur = connection.cursor()

    cur.execute("SELECT * FROM record WHERE dataset in (SELECT DISTINCT id FROM transformed_timeseries)")

    # all transformed timeseries that may be already hold records in the record table for deletion
    all_possible_transformed_timeseries = cur.fetchall()

    tt_size = len(all_possible_transformed_timeseries)
    print("Found {} transformed records in the records table for deletion.".format(tt_size))
    if tt_size > 0:
        # Delete all transforms records
        try:
            transformed_records = cur.execute("DELETE FROM record WHERE dataset in (SELECT id FROM transformed_timeseries)")
            connection.commit()
        except RuntimeError as e:
            print(e)
            print("Error while deleting already existing transformed records. Database operations rolled back.")
            connection.rollback()
        finally:
            cur.close()
            # TODO: is this neccessary?

    #
    # Creating new transformed timeseries records
    #
    cur = connection.cursor()

    # fetch all sources
    # TODO: add target to source
    all_sources = cur.execute("SELECT source FROM tranformed_timeseries tt LEFT JOIN transforms t ON tt.id = t.target")
    all_targets = cur.execute("SELECT DISTINCT target FROM tranformed_timeseries tt LEFT JOIN transforms t ON tt.id = t.target")
    sources = all_sources.fetchall()
    targets = all_targets.fetchall()

    records = dict()

    # fetch all affected target records (cache them locally)
    for target in targets:
        cur.execute("SELECT * FROM record WHERE dataset = %1", (target))
        records[target] = cur.fetchall()

    # then iterate over the sources and insert the transformation into the respective target into the record table
    try:
        for source in sources:

                for rec in records[target]:
                    _rec = transform(rec)
                    cur.execute("INSERT INTO record VALUES (%%)", (rec))
                    # TODO: bulk inserting?
    except RuntimeError as e:
        print(e)
        connection.rollback()
        exit(1)

    print("Everything went fine!")
    connection.commit()
    cur.close()