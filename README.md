This is a set of 3 modules that aim to do some table data pre-processing and/or cleaning so that we can use them for templating into vega-lite graph commands.

- `reader.py` is a module that reads the .csv files one folder deep from the current working directory, and returns a list of `DataTable` objects (which is a convenient way to group the .csv, .meta, and .types files in one object).
- `classifier.py` is a module that takes in a given column (header and records), and classifies that column into one of a list of enumerated column types (e..g temporal, ordinal, quantatitative, etc.).
- `normalizer.py` is a module that, given a specific column type and a list of records, normalizes that list of records into some prespecified form. This is most useful for columns of the temporal type, but could be useful for other column types (like ordinals) as well.

And `main.py` is just a driver program that is able to use these three modules together, and allows for some debugging and/or tests to be written.
