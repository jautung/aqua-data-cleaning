import reader
import classifier
import normalizer

def main():
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
            elif category == "QUANTITATIVE_MONEY":
                norm_records = nmlzr.normalize_money(records)
            elif category == "QUANTITATIVE_PERCENTAGE":
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

if __name__ == "__main__":
    main()
