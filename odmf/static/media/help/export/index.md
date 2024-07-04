# Export data from the structured database

## Export observations

### Export plotted data

The most convenient way to export observation records is to construct a plot of the data
and export the underlying data. A click on "export" opens the export Window, where you can choose the data
format, the output timesteps and evtl. interpolation methods

#### Data formats
- Excel file
- Textfile with comma seperated variables (CSV)
- Textfile with tab seperated variables (TSV)
- JSON Notation (best for web applications)
- Apache parquet format (best for data science applications in eg. Python and R)

### Time steps

The next option chooses the scheme, which time steps should be exported. If you have regular time step
data, eg. from a logger or you have created aggregated timesteps, the selection hardly matters. If
the data you want to export has very irregular timesteps or different times, use the options below
to get data at the time steps you are really interested.
The options are:

- union: All timesteps from all datasets are exported as an own row. Records with the same time are
  put on the same line. If a plot line has no datapoint at the same time as another, a blank field is
  exported. To join nearly identical time steps, you can use a tolerance (see below) 
- intersection: Export only time steps where all plot lines have records. To get more exported lines,
  tolerances are used again
- Regular time steps: Define a time grid, eg. every day (`D`) or every three hours (`3h`) for export.
  records with another time are only exported if they fit the output time tolerance
- Timesteps from plot line: Use the time steps of a certain line and export data from other lines if their
  data points are within the tolerance

### Regular grid and tolerance

If regular grid is selected you can specify the grid using frequncy codes. ODMF uses a
[library which defines many codes](https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases). The most important are:
- `s` Second
- `min` Minute
- `h` Hour
- `D` Day
- `B` Business day
- `W` Week
- `M` Month
- `Y` Year

These codes can be scaled, you can export biweekly with `2W` or every 3 hours as `3h`. A special code,
that cannot be scaled is `decade`, here you get the data reported for three parts of a month, 
day 1-10, day 11-20 and day 21-28/29/30/31.

## Export metadata

Exporting metadata is currently under development. You can export **all** sites at the site list, but 
the export does not respect the filters.

Exporting datasets, logs and pictures is not developed yet.