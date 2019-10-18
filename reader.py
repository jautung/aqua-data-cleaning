import os
import csv
import json

class DataTable:
    def __init__(self, csv_file, meta_file, types_file):
        self.csv_file = csv_file
        self.meta_file = meta_file
        self.types_file = types_file

    def get_col(self, col_idx):
        header = None
        col = []
        with open(self.csv_file) as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                try:
                    value = row[col_idx]
                except IndexError:  # col_idx out of bounds
                    return None
                if header == None:
                    header = value
                else:
                    col.append(value)
        return (header, col)

    def get_meta(self):
        if self.meta_file == None:
            return None
        with open(self.meta_file, "r") as json_file:
            return json.load(json_file)

    def get_type(self, col_idx):
        if self.types_file == None:
            return None
        with open(self.types_file, "r") as file:
            line = file.readline()
            types = line.split(",")
            if col_idx >= len(types):
                return None
            return types[col_idx]

class Reader:
    def __init__(self):
        pass

    # returns list of DataTable objects, i.e. csv files that are 1 folder deep from pwd
    # limit is used to limit the number of DataTables retrieved
    def get_data_tables(self, limit=None):
        data_tables = []
        num_data_tables = 0

        folders = [folder for folder in os.listdir(".") if os.path.isdir(folder)]
        for folder in folders:
            files = set(os.listdir(folder))
            for file in files:
                (filename, extension) = os.path.splitext(file)
                if extension == ".csv":
                    if (filename + ".meta") in files:
                        meta_filepath = os.path.join(folder, filename + ".meta")
                    else:
                        meta_filepath = None
                    if (filename + ".types") in files:
                        types_filepath = os.path.join(folder, filename + ".types")
                    else:
                        types_filepath = None
                    data_tables.append(DataTable(os.path.join(folder, file), meta_filepath, types_filepath))
                    num_data_tables += 1
                    if limit != None and num_data_tables >= limit:
                        return data_tables

        return data_tables
