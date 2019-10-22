import reader
import classifier
import normalizer

# runs the classifier and the normalizer on all data tables, up to a limit of num_tables
# prints to stdout the result for all columns that got classified into one of the filter_categories
def classify_then_normalize(num_tables=None, filter_categories=[]):
    rdr = reader.Reader()
    clssfr = classifier.Classifier()
    nmlzr = normalizer.Normalizer()

    data_tables = rdr.get_data_tables(num_tables)
    for data_table in data_tables:
        col_idx = 0
        while True:
            col = data_table.get_col(col_idx)
            if col == None:  # out of columns to read
                break

            (header, records) = col
            category = clssfr.classify(col_idx, header, records)

            # filtering of results
            if category in filter_categories:
                if category == "ROW_NUM":
                    norm_records = nmlzr.normalize_quant_default(header, records)
                elif category == "ORDINAL":
                    norm_records = nmlzr.normalize_ordinal(header, records)
                elif category == "TEMPORAL":
                    (norm_records, vega_lite_timeunit) = nmlzr.normalize_temporal(header, records)
                elif category == "TEMPORAL_RANGE":
                    (norm_records_starts, norm_records_ends, vega_lite_timeunit) = nmlzr.normalize_temporal_range(header, records)
                elif category == "QUANT_MONEY":
                    (norm_records, units) = nmlzr.normalize_money(header, records)
                elif category == "QUANT_PERCENT":
                    norm_records = nmlzr.normalize_percent(header, records)
                    units = "%"
                elif category == "QUANT_LENGTH" or category == "QUANT_AREA" or category == "QUANT_SPEED":
                    (norm_records, units) = nmlzr.normalize_quant_units(header, records)
                elif category == "QUANT_OTHER":
                    norm_records = nmlzr.normalize_quant_default(header, records)
                    units = None
                elif category == "QUANT_RANGE":
                    (norm_records_starts, norm_records_ends) = nmlzr.normalize_quant_range(header, records)
                    units = None
                else:  # CATEGORICAL and STRING
                    norm_records = nmlzr.normalize_default(header, records)

                print("====================================================================================")
                print("Column      :", data_table.csv_file, "(Column " + str(col_idx) + ")")
                print("Header      :", repr(header))
                meta = data_table.get_meta()
                if meta != None:
                    print("Meta        :", meta)
                print("Original    :", records)
                print()

                print("Classified  :", category)
                if category.endswith("_RANGE"):
                    print("Normalized s:", norm_records_starts)
                    print("Normalized e:", norm_records_ends)
                else:
                    print("Normalized  :", norm_records)
                if category.startswith("TEMPORAL"):
                    print("VL timeunit :", vega_lite_timeunit)
                elif category.startswith("QUANT_"):
                    print("Units       :", units)
                print()

            col_idx += 1

# add verbose to print out all results, not verbose to print out only incorrect classifications
# tests are currently manually-labeled columns of some of the .csv files
def classification_test(verbose=True):
    rdr = reader.Reader()
    clssfr = classifier.Classifier()

    test_data_tables = rdr.get_classifier_test_data_tables()
    correct_count = 0
    total_count = 0
    for data_table in test_data_tables:
        col_idx = 0
        while True:
            col = data_table.get_col(col_idx)
            if col == None:  # out of columns to read
                break

            (header, records) = col
            classified_type = clssfr.classify(col_idx, header, records)
            correct_type = data_table.get_type(col_idx)
            if verbose or classified_type != correct_type:
                print("Column    :", data_table.csv_file, "(Column " + str(col_idx) + ")")
                print("Classified:", classified_type)
                print("Correct   :", correct_type)
            if verbose and classified_type == correct_type:
                print()
            if classified_type == correct_type:
                correct_count += 1
            else:
                print("Header    :", repr(header))
                print("Records   :", records)
                print()
            total_count += 1

            col_idx += 1

    print("===================================================")
    print("Overall result:", str(correct_count) + "/" + str(total_count), "(" + str(round(correct_count / total_count * 100, 2)) + "%)", "correct classifications")

if __name__ == "__main__":
    classify_then_normalize(50, ["TEMPORAL"])
    # classification_test(False)
