import num2words
import dateutil.parser

class Classifier:
    # @max_records_checked: max number of records we check for a specific format
    #   - higher values mean more accuracy, but slower program execution
    #   - None means no limit, i.e. check all of the records
    # @threshold_for_match: fraction of those records that need to match to be classified
    # @ordinal_bound: bound for which we will be able to recognize ordinals
    # @categorical_distinctness_threshold: upper bound on fraction of distinct records needed to be categorical
    #   - higher values mean we accept more things to be categorical
    def __init__(self, max_records_checked=None,
                       threshold_for_match=1.0,
                       ordinal_bound=1000,
                       categorical_distinctness_threshold=0.1):
        self.max_records_checked = max_records_checked
        self.threshold_for_match = threshold_for_match
        self.ordinals = set()
        for i in range(ordinal_bound):
            self.ordinals.add(num2words.num2words(i, to="ordinal").lower())
            self.ordinals.add(num2words.num2words(i, to="ordinal_num"))
        self.categorical_distinctness_threshold = categorical_distinctness_threshold

    # @header: the column header in a DataTable
    # @records: a list of records for that column
    # returns one of the following categories (strings)
    #  - "ORDINAL"
    #  - "TEMPORAL"
    #  - "QUANT_MONEY"
    #  - "QUANT_LENGTH"
    #  - "QUANT_AREA"
    #  - "QUANT_PERCENTAGE"
    #  - "QUANT_OTHER"
    #  - "CATEGORICAL"
    #  - "STRING"
    def classify(self, header, records):
        # determining number of records to check
        if self.max_records_checked == None:
            records_to_check = len(records)
        else:
            records_to_check = min(self.max_records_checked, len(records))

        # ordinal
        num_ordinals_found = 0
        for record_idx in range(records_to_check):
            if records[record_idx].lower() in self.ordinals:
                num_ordinals_found += 1
        if num_ordinals_found >= self.threshold_for_match * records_to_check:
            return "ORDINAL"

        # temporal
        # NOTE: unfortunately, still matches things like
        #  - Record: ['0-2-0', '1-2-0', '1-3-0', '2-3-0', '2-4-0', '2-5-0', '2-6-0', '2-6-1', '3-6-1', '3-7-1', '4-7-1']
        #  - Tally: ['2-12', '3-7', '3-5', '1-11', '0-13', '1-10', '2-5', '2-5', '1-7', '1-6', '3-0']
        num_temporals_found = 0
        for record_idx in range(records_to_check):
            try:
                # ensures that dateutil is not just recognizing one arbitrary float as a date
                float(records[record_idx].replace(",", "."))
            except ValueError:
                try:
                    dateutil.parser.parse(records[record_idx])
                except ValueError:
                    pass
                else:
                    num_temporals_found += 1
        if num_temporals_found >= self.threshold_for_match * records_to_check:
            return "TEMPORAL"

        # quantitative money
        num_money_found = 0
        for record_idx in range(records_to_check):
            if records[record_idx].startswith("$"):
                num_money_found += 1
        if num_money_found >= self.threshold_for_match * records_to_check:
            return "QUANT_MONEY"

        # quantitative percentage
        num_percentage_found = 0
        for record_idx in range(records_to_check):
            if records[record_idx].endswith("%"):
                num_percentage_found += 1
        if num_percentage_found >= self.threshold_for_match * records_to_check:
            return "QUANT_PERCENTAGE"

        # categorical variable test
        # https://datascience.stackexchange.com/questions/9892/how-can-i-dynamically-distinguish-between-categorical-data-and-numerical-data
        distinct_records = set()
        for record in records:
            distinct_records.add(record)
        if len(distinct_records) < self.categorical_distinctness_threshold * len(records):
            return "CATEGORICAL"

        num_quantities_found = 0
        for record_idx in range(records_to_check):
            try:
                float(records[record_idx].replace(",", ""))
            except ValueError:
                pass
            else:
                num_quantities_found += 1
        if num_quantities_found >= self.threshold_for_match * records_to_check:
            return "QUANT_OTHER"

        return "STRING"
