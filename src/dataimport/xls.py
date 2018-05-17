import xlrd
from os.path import basename, splitext
from datetime import datetime, timedelta

# XlsImportDescription
from glob import glob
from configparser import RawConfigParser
import os.path as op

from .base import AbstractImport, ImportDescription, ImportColumn


class XlsImport (AbstractImport):
    """ Special class for importing xls files. """

    def __init__(self, filename, user, siteid, instrumentid=None,
                 startdate=None, enddate=None):
        AbstractImport.__init__(self, filename, user, siteid, instrumentid,
                                startdate, enddate)

        self.descriptor = ImportDescription.from_file(self.filename)
        self.instrumentid = self.descriptor.instrument
        self.commitinterval = 10000
        self.datasets = {}

    def loadvalues(self):
        """
        Generator function, yields the values from the file as
        a dictionary for each import column
        """

        # There are 4 kinds of date columns in an excel sheet:
        #
        #  1 column:
        #    -> with excel date type
        #    -> with date as text
        #
        #  2 columns:
        #    -> with excel date type
        #    -> with date as text

        # Document date types to decide only once what date type the document has
        DOCUMENT_DATETYPE_DATE_1C = 0
        DOCUMENT_DATETYPE_DATE_2C = 1
        DOCUMENT_DATETYPE_TEXT_1C = 2
        DOCUMENT_DATETYPE_TEXT_2C = 3

        # Same as above, but this time it's to save the time column when two
        # columns are chosen
        DATETYPE_TIME_AT_COL1 = 0
        DATETYPE_TIME_AT_COL2 = 1

        # Helper Functions
        def get_time(date, time, t0=datetime(1899, 12, 30)):
            """
            Parses the datetime from a date and time float value from an excel
            sheet

            :param date: float value
            :param time: float value
            :param t0: datetime object where the computation of time should
                       begin
            :return: datetime object
            """
            if not time:
                return t0 + timedelta(date)
            else:
                if time > 1.000001:
                    time -= int(time)
                    date = int(date)
                    return t0 + timedelta(date + time)

        def intime(time):
            """
            Checks if time is between startdate and enddate

            :param time:
            :return:
            """
            return ((not self.startdate) or time >= self.startdate) and \
                   ((not self.enddate) or time <= self.enddate)

        def inrange(desc, value):
            """
            Tests if the value is inside the boundaries given by the column
            description

            :param desc:
            :param value:
            :return:
            """
            return desc.minvalue <= value <= desc.maxvalue

        def determine_date(datetype, datepos, row, date_cols):
            """
            Determine the date in the given rows

            :param datetype: DOCUMENT_DATETYPE_* static variable
            :param datepos: DATETYPE_TIME_AT_COL* static variable
            :param row: actual row for extract the date
            :param date_cols: list of date col indicies
            :return: datetime object
            """
            if datetype == DOCUMENT_DATETYPE_DATE_1C:
                return get_time(row[date_cols[0]].value, None)
                # d = xlrd.xldate_as_tuple(
                #    row[date_cols[0]], sheet.datemode)
                #d = datetime(d[2], d[1], d[0])
            elif datetype == DOCUMENT_DATETYPE_TEXT_1C:
                return datetime.strptime(row[date_cols[0]].value,
                                         self.descriptor.dateformat)
            elif datetype == DOCUMENT_DATETYPE_DATE_2C:
                # TODO: Philipp nachfragen, reicht ein vergleich kleiner 0 groesser 0
                if datepos == DATETYPE_TIME_AT_COL1:
                    return get_time(row[date_cols[1]].value,
                                    row[date_cols[0]].value)
                elif datepos == DATETYPE_TIME_AT_COL2:
                    return get_time(row[date_cols[0]].value,
                                    row[date_cols[1]].value)
            elif datetype == DOCUMENT_DATETYPE_TEXT_2C:
                return datetime.strptime(row[date_cols[0]] +
                                         row[date_cols[1]],
                                         self.descriptor.dateformat)

        def determine_datetype(data_row, cols):
            '''
            Determine the type of the date in the given cols

            :param data_row: len(data_row) >= len(cols)
            :param cols: 0 < len(cols) <= 2
            :return: Returns one of the static variables if its text or an date
                    and if its one column or two column
            '''
            if len(cols) == 1:
                # One column
                if data_row[cols[0]].ctype == xlrd.XL_CELL_DATE:
                    return DOCUMENT_DATETYPE_DATE_1C
                elif data_row[cols[0]].ctype == xlrd.XL_CELL_TEXT:
                    return DOCUMENT_DATETYPE_TEXT_1C
            elif len(cols) == 2:
                # Two columns
                if data_row[cols[0]].ctype == xlrd.XL_CELL_DATE \
                        and data_row[cols[1]].ctype == xlrd.XL_CELL_DATE:
                    return DOCUMENT_DATETYPE_DATE_2C
                elif data_row[cols[0]].ctype == xlrd.XL_CELL_TEXT \
                        and data_row[cols[1]].ctype == xlrd.XL_CELL_TEXT:
                    return DOCUMENT_DATETYPE_TEXT_2C
            else:
                raise ValueError("You should give at least one and " +
                                 "maximum two datecolumns. In your "
                                 "config file '" +
                                 len(self.descriptor.datecolumns) +
                                 "' are given")

        def determine_timepos(data_row, cols, ddt):
            """
            Determines the position of the time column in the list of the two
            text or date columns

            :param data_row: actual row
            :param cols: list of two indicies
            :param ddt: document date type as one of DOCUMENT_DATETYPE_*
                variables
            :return:
            """
            if ddt == DOCUMENT_DATETYPE_DATE_2C:
                if data_row[cols[0]].value < 0:
                    return DATETYPE_TIME_AT_COL1

                elif data_row[cols[1]] < 0:
                    return DATETYPE_TIME_AT_COL2
            elif ddt == DOCUMENT_DATETYPE_TEXT_2C:
                if ':' in data_row[cols[0]]:
                    return DATETYPE_TIME_AT_COL1

                elif ':' in data_row[cols[1]]:
                    return DATETYPE_TIME_AT_COL2

        # Opens the xlrd filestream
        # Using on_demand flag for resource saving
        # Using with statement for implicit call (Book)fin.release_resources()
        # cause of using the on_demand flag
        with xlrd.open_workbook(self.filename, on_demand=True) as fin:

            # Holds the result
            res = None

            # Grant config premise
            n = self.descriptor.skiplines  # n = actual line number

            # Check if only one sheet
            # TODO: Write this down in a wiki entry that the first sheet will chosen
            sheet = XlsImport.open_sheet(fin, self.descriptor.filename,
                                         self.descriptor.worksheet,
                                         self.errorstream)

            # Ready to load data

            # For not making the date check more than one time
            # Cause the date columns have one layout per file
            document_datetype = None
            datetype_timepos = None

            # Saving some keyboard strokes
            date_cols = self.descriptor.datecolumns

            # Dictionary for saving the stats
            stats = dict(total_rows=sheet.nrows,
                         not_intime=0,
                         not_inrange=0)

            # Check if there are rows to process
            if n >= sheet.nrows:
                for s in fin.sheets():
                    print(s.nrows, "Rows in sheet ", s)
                raise ValueError("Fatal, no rows to process n = %d and rows = "
                                 "%d. Check if you save in a supported excel "
                                 "version" % (n, sheet.nrows))
            # Temporary variable for holding the last completely computed result
            # (for calculating the difference)
            lastres = None

            # Row-wise
            while n < sheet.nrows:
                row = sheet.row(n)

                # Only when hasval is set and the loop has computed a result
                # lastres is set to res (e.g. tipping bucket: for calculating
                # the difference)
                hasval = False

                # Check the date and get it into result object
                if date_cols:
                    # Even if the else branch is most likely always executed
                    # first the if branch is used even more. So i decided to
                    # switch the code
                    if document_datetype:
                        # Already determinated a datetype

                        # Only extract the date out of the row
                        d = determine_date(document_datetype, datetype_timepos,
                                           row, date_cols)
                    else:
                        # There is no datetype determinated yet

                        document_datetype = determine_datetype(row, date_cols)
                        # When there are two columns, determine the pos of the
                        # time column too
                        if document_datetype == DOCUMENT_DATETYPE_DATE_2C or \
                                document_datetype == DOCUMENT_DATETYPE_TEXT_2C:
                            datetype_timepos = determine_timepos(
                                row, date_cols, document_datetype)

                        d = determine_date(document_datetype, datetype_timepos,
                                           row, date_cols)

                    if not intime(d):
                        stats['not_intime'] += 1
                        n += 1
                        continue

                    res = dict(d=d)

                # Iter through the row/cols
                for c in self.descriptor.columns:

                    # Value validation
                    # now added nodata validation
                    if row[c.column] is not None \
                            and row[c.column] is not ''\
                            and row[c.column] not in self.descriptor.nodata:

                        if inrange(c, row[c.column].value):
                            # TODO: Philip fragen (Ist das so ok?)
                            # TODO: Ist eine Datenspalte immer float konform
                            res[c.column] = float(row[c.column].value)
                            hasval = True
                            if c.difference and lastres:
                                res[c.column] = (res[c.column] -
                                                 lastres[c.column]) * c.factor
                            else:
                                res[c.column] = res[c.column] * c.factor
                        else:
                            stats['not_inrange'] += 1
                            res[c.column] = None
                    else:
                        res[c.column] = None

                # yield value
                if hasval:
                    lastres = res
                n += 1
                yield res

            print("Function 'loadvalues' successfully!\n"
                  "  Stats\n"
                  "  ->\tRows total:\t\t%d\n"
                  "  ->\tCells not_inrange:\t%d\n"
                  "  ->\tRows not_intime:\t%d\n" % (stats['total_rows'] -
                                                    self.descriptor.skiplines,
                                                    stats['not_inrange'],
                                                    stats['not_intime']))

    @staticmethod
    def extension_fits_to(filename):
        """

        :param filename:
        :return:
        """
        name, ext = splitext(filename)
        return ext.lower() == '.xls' or ext.lower() == '.xlsx'

    @staticmethod
    def open_sheet(xlsfiledesc, filename, worksheet_index, err):
        """

        :param xlsfiledesc:
        :return:
        """
        if xlsfiledesc.nsheets != 0:
            if xlsfiledesc.nsheets != 1:
                err.write("WARNING: xls file with more than one "
                          "sheet specified at '%s'. "
                          "Chose the sheet at index '%i'.\n"
                          % (filename, worksheet_index - 1))
            return xlsfiledesc.sheet_by_index(worksheet_index - 1)
        else:

            err.write("ERROR: Please make sure there is a "
                      "sheet. Xls file '%s' has no sheets!\n"
                      % filename)
            # Stops the generator - see PEP 380
            # https://www.python.org/dev/peps/pep-0380/
            raise StopIteration("ERROR: Please make sure there is a sheet."
                                " Xls file '%s' has no sheet specified !\n"
                                % filename)
