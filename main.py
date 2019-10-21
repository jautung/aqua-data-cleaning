import reader
import classifier
import normalizer

def debug():
    rdr = reader.Reader()
    clssfr = classifier.Classifier()
    nmlzr = normalizer.Normalizer()

    data_tables = rdr.get_data_tables()
    for data_table in data_tables:
        col_idx = 0
        while True:
            col = data_table.get_col(col_idx)
            if col == None:  # out of columns to read
                break

            (header, records) = col
            category = clssfr.classify(header, records)

            if category == "ORDINAL":
                norm_records = nmlzr.normalize_ordinal(records)
            elif category == "TEMPORAL":
                (norm_records, vega_lite_timeunit) = nmlzr.normalize_temporal(records)
            elif category == "QUANT_MONEY":
                norm_records = nmlzr.normalize_money(records)
            elif category == "QUANT_PERCENTAGE":
                norm_records = nmlzr.normalize_percentage(records)
            else:  # other categories
                norm_records = nmlzr.normalize_default(records)

            # condition added for debug filtering of results
            if category == "TEMPORAL":
                print("====================================================================================")
                print("Column      :", data_table.csv_file, "(Column " + str(col_idx) + ")")
                print("Header      :", header)
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

# verbose to print out all results, not verbose to print out only incorrect classifications
def classify_test(verbose=True):
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
            classified_type = clssfr.classify(header, records)
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
                print("Records   :", records)
                print()
            total_count += 1

            col_idx += 1

    print("===================================================")
    print("Overall result:", str(correct_count) + "/" + str(total_count), "correct classifications")

if __name__ == "__main__":
    classify_test(verbose=True)
