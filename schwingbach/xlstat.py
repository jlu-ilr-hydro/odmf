import sys
import xlrd


def getLastRow(sh, col_num=None):
    """
    ;param sh: Excel worksheet
    ;param col_num: long/integer identifying which column to query
    """
    if not col_num == None:
        return sh.nrows

    for r in range(sh.nrows, 1, -1):
        if str(sh.col_values(col_num)[r - 1]).strip() == '':
            print 'cell({},{}) contains an empty value or trims to empty string'.format(
                r, col_num)
        else:
            return r


def my_last_row(sh, col):
    n = 0
    has_exit = False
    try:

        while sh.cell(n, col):
            n += 1
    except IndexError as e:
        has_exit = True

    if has_exit:
        print "Exited with IndexError"
    return n


print "Stats for file '%s'" % sys.argv[1]

fin = xlrd.open_workbook(sys.argv[1])

for sno, s in enumerate(fin.sheets()):
   print "MYROW - Sheet %d has %d rows - %s" % (sno, s.nrows, s)
