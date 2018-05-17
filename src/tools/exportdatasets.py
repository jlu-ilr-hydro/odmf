'''
Exports the climate datasets as one table with multiple columns

Created on 05.06.2013

@author: kraft-p
'''
import db
from io import StringIO
import codecs
from traceback import format_exc as traceback
import sys
from datetime import datetime, timedelta
import matplotlib.dates
t0 = datetime(1, 1, 1)


def num2date(t):
    return t0 + timedelta(days=t)


def exportLines(fout, lines, tolerance=60):
    """
    Exports multiple lines from a plot as a table with each line as a column
    To align the values in the rows a tolerance is chosen, by which measure
    times may differ, but should still be combined in the same row.
    """
    # Make sure the tolerance is > 0
    tolerance = max(tolerance, 0.01)

    # prepare the output file, Excel needs the BOM to recognize csv files with
    # UTF-8
    fout.write(codecs.BOM_UTF8.decode('utf-8'))

    # simplify fileoutput
    def writeline(line):
        fout.write(','.join((str(s)
                             if s else '') for s in line) + '\n')

    # Write headers
    fout.write('time,')
    writeline(lines)
    fout.write('\n')

    # Load all time and value arrays for the lines. This is a huge memory
    # consumer
    tvpairs = [l.load() for l in lines]
    # Create counters, holding the position of a line point
    counters = [0] * len(tvpairs)
    # Last time step
    told = 0.0
    # Hold the data of the current line
    linedata = []
    # Loop on with the counters until all data is consumed
    while any(c < len(tv[0]) for c, tv in zip(counters, tvpairs)):
        # Get the current time step
        t = min(tv[0][c] for c, tv in zip(counters, tvpairs) if c < len(tv[0]))
        # If the current time step is past the tolerance time in seconds
        if t - told >= tolerance / 86400.:
            # Get the datetime
            time = matplotlib.dates.num2date(t).strftime("%Y-%m-%d %H:%M:%S")
            # Save the current linedata to the file
            if linedata:
                writeline(linedata)
            # Make a new linedata
            linedata = [time] + ([None] * len(lines))
            # Current t gets the old time
            told = t

        # Populate the linedata for each line
        for i in range(len(lines)):
            # Check if there is data left and the current data is inside the
            # tolerance time
            if (counters[i] < len(tvpairs[i][0]) and
                    tvpairs[i][0][counters[i]] - t < tolerance):
                # Get the value
                linedata[i + 1] = tvpairs[i][1][counters[i]]
                # Move on with counter
                counters[i] += 1
