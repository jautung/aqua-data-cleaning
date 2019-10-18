import num2words
import dateutil.parser

class Classifier:
    # @max_records_checked: max number of records we check for a specific format
    #   - higher values mean more accuracy, but slower program execution
    # @threshold_for_match: fraction of those records that need to match to be classified
    # @ordinal_bound: bound for which we will be able to recognize ordinals
    # @categorical_distinctness_threshold: upper bound on fraction of distinct records needed to be categorical
    #   - higher values mean we accept more things to be categorical
    def __init__(self, max_records_checked=50, 
                       threshold_for_match=0.8,
                       ordinal_bound=1000,
                       categorical_distinctness_threshold=0.1):
        self.max_records_checked = max_records_checked
        self.threshold_for_match = threshold_for_match
        self.ordinals = set()
        for i in range(ordinal_bound):
            self.ordinals.add(num2words.num2words(i, to="ordinal").lower())
            self.ordinals.add(num2words.num2words(i, to="ordinal_num"))

    # @header: the column header in a DataTable
    # @records: a list of records for that column
    # returns one of the following categories (strings)
    #  - "ORDINAL"
    #  - "TEMPORAL"
    #  - "QUANTITATIVE_MONEY"
    #  - "QUANTITATIVE_LENGTH"
    #  - "QUANTITATIVE_AREA"
    #  - "QUANTITATIVE_PERCENTAGE"
    #  - "QUANTITATIVE_OTHER"
    #  - "CATEGORICAL"
    #  - "UNSTRUCTURED"
    def classify(self, header, records):
        # header checkers
        if header.lower() == "date" or header.lower() == "year":
            return "TEMPORAL"
        if header.lower() == "price":
            return "QUANTITATIVE_MONEY"
        if header.lower() == "distance" or header.lower() == "length":
            return "QUANTITATIVE_LENGTH"

        # record checkers
        records_to_check = min(self.max_records_checked, len(records))

        # ordinal
        num_ordinals_found = 0
        for record_idx in range(records_to_check):
            if records[record_idx].lower() in self.ordinals:
                num_ordinals_found += 1
        if num_ordinals_found > self.threshold_for_match * records_to_check:
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
        if num_temporals_found > self.threshold_for_match * records_to_check:
            return "TEMPORAL"

        # quantitative money
        num_money_found = 0
        for record_idx in range(records_to_check):
            if records[record_idx].startswith("$"):
                num_money_found += 1
        if num_money_found > self.threshold_for_match * records_to_check:
            return "QUANTITATIVE_MONEY"

        # quantitative percentage
        num_percentage_found = 0
        for record_idx in range(records_to_check):
            if records[record_idx].endswith("%"):
                num_percentage_found += 1
        if num_percentage_found > self.threshold_for_match * records_to_check:
            return "QUANTITATIVE_PERCENTAGE"

        # categorical variable test
        # https://datascience.stackexchange.com/questions/9892/how-can-i-dynamically-distinguish-between-categorical-data-and-numerical-data
        distinct_records = set()
        for record in records:
            distinct_records.add(record)
        if len(distinct_records) < 0.2 * len(records):
            return "CATEGORICAL"

        num_quantities_found = 0
        for record_idx in range(records_to_check):
            try:
                float(records[record_idx].replace(",", ""))
            except ValueError:
                pass
            else:
                num_quantities_found += 1
        if num_quantities_found > self.threshold_for_match * records_to_check:
            return "QUANTITATIVE_OTHER"

        return "UNSTRUCTURED"
