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

            if category == "ORDINAL":
                norm_records = nmlzr.normalize_ordinal(records)
            elif category == "TEMPORAL":
                (norm_records, vega_lite_timeunit) = nmlzr.normalize_temporal(records)
            elif category == "QUANT_MONEY":
                norm_records = nmlzr.normalize_money(records)
            elif category == "QUANT_PERCENT":
                norm_records = nmlzr.normalize_percentage(records)
            else:  # other categories
                norm_records = nmlzr.normalize_default(records)

            # filtering of results
            if category in filter_categories:
                print("====================================================================================")
                print("Column      :", data_table.csv_file, "(Column " + str(col_idx) + ")")
                print("Header      :", repr(header))
                meta = data_table.get_meta()
                if meta != None:
                    print("Meta        :", meta)
                print("Original    :", records)
                print()

                print("Current type:", data_table.get_type(col_idx))
                print("New type    :", category)
                print("Normalized  :", norm_records)
                if category == "TEMPORAL":
                    print("VL timeunit :", vega_lite_timeunit)
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
    # classify_then_normalize(500, ["TEMPORAL_RANGE"])
    classification_test(False)
