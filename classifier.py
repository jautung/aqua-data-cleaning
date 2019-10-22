import num2words
import dateutil.parser
import pint
import re

# taken from https://stackoverflow.com/questions/5319922/python-check-if-word-is-in-a-string
def find_whole_word(w):
    return re.compile(r'\b({0})\b'.format(w), flags=re.IGNORECASE).search

class Classifier:
    # @max_records_checked: max number of records we check for a specific format
    #   - higher values mean more accuracy, but slower program execution
    #   - None means no limit, i.e. check all of the records
    # @threshold_for_match: fraction of those records that need to match to be classified
    # @ordinal_bound: bound for which we will be able to recognize ordinals
    # @categorical_distinctness_threshold: upper bound on fraction of distinct/total to be classified as categorical
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

    # @col_idx: the column index in a DataTable
    # @header: the column header in a DataTable
    # @records: a list of records for that column
    # returns one of the following categories (strings)
    #  - "ROW_NUM" (this is meaningless)
    #  - "ORDINAL"
    #  - "TEMPORAL"
    #  - "TEMPORAL_RANGE"
    #  - "QUANT_MONEY"
    #  - "QUANT_PERCENT"
    #  - "QUANT_LENGTH"
    #  - "QUANT_AREA"
    #  - "QUANT_SPEED"
    #  - "QUANT_OTHER"
    #  - "QUANT_RANGE"
    #  - "CATEGORICAL"
    #  - "STRING"
    def classify(self, col_idx, header, records):
        # some tables have the first column corresponding to row number
        if col_idx == 0:
            is_row_num = True
            for record_idx in range(len(records)):
                try:
                    record_num = float(records[record_idx])
                except ValueError:
                    is_row_num = False
                    break
                else:
                    if record_idx + 1 != record_num:
                        is_row_num = False
                        break
            if is_row_num:
                # but sometimes this just corresponds to rank or position
                if header.lower() == "rank" or header.lower() == "position" or header.lower() == "pos":
                    return "ORDINAL"
                else:
                    return "ROW_NUM"

        # determining number of records to check
        if self.max_records_checked == None:
            records_to_check = len(records)
        else:
            records_to_check = min(self.max_records_checked, len(records))

        # ordinal checker
        num_ordinals_found = 0
        for record_idx in range(records_to_check):
            if records[record_idx].lower() in self.ordinals:
                num_ordinals_found += 1
        if num_ordinals_found >= self.threshold_for_match * records_to_check:
            return "ORDINAL"

        # temporal checker
        num_temporals_found = 0
        for record_idx in range(records_to_check):
            try:
                # ensures that dateutil is not just recognizing one random float as a date
                float(records[record_idx])
            except ValueError:
                try:
                    dateutil.parser.parse(records[record_idx])
                except ValueError:
                    pass
                else:
                    num_temporals_found += 1
        if num_temporals_found >= self.threshold_for_match * records_to_check:
            return "TEMPORAL"

        # temporal range checker
        num_temporal_ranges_found = 0
        for record_idx in range(records_to_check):
            if records[record_idx].count("-") == 1:
                (first, second) = records[record_idx].split("-")
                try:
                    # ensures that dateutil is not just recognizing random floats as a date
                    float(first.replace(",", ""))
                    float(second.replace(",", ""))
                except ValueError:
                    try:
                        dateutil.parser.parse(first)
                        dateutil.parser.parse(second)
                    except ValueError:
                        pass
                    else:
                        num_temporal_ranges_found += 1
        if num_temporal_ranges_found >= self.threshold_for_match * records_to_check:
            return "TEMPORAL_RANGE"

        # quant range checker
        num_quant_ranges_found = 0
        for record_idx in range(records_to_check):
            if records[record_idx].count("-") == 1:
                (first, second) = records[record_idx].split("-")
                try:
                    float(first.replace(",", ""))
                    float(second.replace(",", ""))
                except ValueError:
                    pass
                else:
                    num_quant_ranges_found += 1
        if num_quant_ranges_found >= self.threshold_for_match * records_to_check:
            if header.lower() == "year" or header.lower() == "years":
                return "TEMPORAL_RANGE"
            else:
                return "QUANT_RANGE"

        # money checker
        num_money_found = 0
        for record_idx in range(records_to_check):
            if records[record_idx].startswith("$"):
                num_money_found += 1
        if num_money_found >= self.threshold_for_match * records_to_check:
            return "QUANT_MONEY"

        # percentage checker
        num_percent_found = 0
        for record_idx in range(records_to_check):
            if records[record_idx].endswith("%"):
                num_percent_found += 1
        if num_percent_found >= self.threshold_for_match * records_to_check:
            return "QUANT_PERCENT"

        # using pint package to check and parse for units
        ureg = pint.UnitRegistry()
        freq_of_units = dict()
        for record_idx in range(records_to_check):
            try:
                quant = ureg.parse_expression(records[record_idx])
            except:
                continue
            if isinstance(quant, int) or isinstance(quant, float):  # already a number, no units
                continue
            unit = quant.units
            freq_of_units[unit] = freq_of_units.get(unit, 0) + 1
        if len(freq_of_units) > 0:
            sorted_freq_of_units = sorted(freq_of_units.items(), key=lambda x: x[1], reverse=True)
            (most_common_unit, most_common_freq) = sorted_freq_of_units[0]
            if most_common_freq >= self.threshold_for_match * records_to_check:
                dim = dict(ureg.parse_expression(str(most_common_unit)).dimensionality)
                if len(dim) == 1 and dim.get("[length]") == 1:
                    return "QUANT_LENGTH"
                elif len(dim) == 1 and dim.get("[length]") == 2:
                    return "QUANT_AREA"
                elif len(dim) == 2 and dim.get("[length]") == 1 and dim.get("[time]") == -1:
                    return "QUANT_SPEED"
                else:  # some unit that we don't know about, or don't want to parse
                    return "STRING"

        # preliminary categorical checker
        # https://datascience.stackexchange.com/questions/9892/how-can-i-dynamically-distinguish-between-categorical-data-and-numerical-data
        distinct_records = set()
        for record in records:
            distinct_records.add(record)
        if len(distinct_records) < self.categorical_distinctness_threshold * len(records):
            return "CATEGORICAL"

        # remains to distinguish QUANT_OTHER, CATEGORICAL, and STRING as best as possible
        # classifies QUANT_<UNIT> if the unit is in the header
        # classifies TEMPORAL if the column has only years, based on header again
        are_floats = False
        are_ints = False
        num_floats_found = 0
        num_ints_found = 0
        for record_idx in range(records_to_check):
            try:
                float(records[record_idx].replace(",", ""))
            except ValueError:
                pass
            else:
                num_floats_found += 1
                try:
                    int(records[record_idx].replace(",", ""))
                except ValueError:
                    pass
                else:
                    num_ints_found += 1
        if num_floats_found >= self.threshold_for_match * records_to_check:
            are_floats = True
            if num_ints_found >= self.threshold_for_match * records_to_check:
                are_ints = True

        if not are_floats:
            return "STRING"
        elif are_floats and not are_ints:
            if find_whole_word("usd")(header) != None or "($)" in header:
                return "QUANT_MONEY"
            elif find_whole_word("pct")(header) != None or find_whole_word("percent")(header) != None or find_whole_word("percentage")(header) != None:
                return "QUANT_PERCENT"
            elif find_whole_word("length")(header) != None or find_whole_word("distance")(header) != None:
                return "QUANT_LENGTH"
            elif find_whole_word("area")(header) != None:
                return "QUANT_AREA"
            elif find_whole_word("speed")(header) != None:
                return "QUANT_SPEED"
            else:
                return "QUANT_OTHER"
        else:  # are_ints
            # a lot more parsing here
            # check for years in temporal
            # check for possible categorical if all integers
            # check for units in the header
            # check for normality of the data as well
            return "TBD"
