import num2words
import re
import itertools
import dateutil.parser
import datetime

class Normalizer:
    # @ordinal_bound: bound for which we will be able to recognize ordinals
    def __init__(self, ordinal_bound=1000):
        self.ordinal_normalizer_dict = dict()
        for i in range(ordinal_bound):
            self.ordinal_normalizer_dict[num2words.num2words(i, to="ordinal").lower()] = i
            self.ordinal_normalizer_dict[num2words.num2words(i, to="ordinal_num")] = i

    # auxiliary function
    # adapted from https://stackoverflow.com/questions/53892450/get-the-format-in-dateutil-parse
    # leverages dateutil.parser's parse function, then matches returned date against tokens of date_str (backwards engineering)
    # returns a tuple of equal-length lists (specifier_strings, specifier_types_used)
    def find_candidate_date_formats(self, date_str):
        # correct date according to dateutil.parser
        try:
            date = dateutil.parser.parse(date_str)
        except ValueError:  # unable to parse date_str as a date in the first place
            return ([], [])

        # decomposing possible components of the correct date
        specifiers = {
            "%a": "Weekday", # weekday abbreviated
            "%A": "Weekday", # weekday in full
            "%d": "Day",     # day of month zero-padded
            "%-d": "Day",    # day of month decimal
            "%b": "Month",   # month abbreviated
            "%B": "Month",   # month in full
            "%m": "Month",   # numeric month zero-padded
            "%-m": "Month",  # numeric month decimal
            "%y": "Year",    # year without century zero-padded
            "%Y": "Year",    # year with century decimal
            "%H": "Hour",    # hour (24H) zero-padded
            "%-H": "Hour",   # hour (24H) decimal
            "%I": "Hour",    # hour (12H) zero-padded
            "%-I": "Hour",   # hour (12H) decimal
            "%M": "Minute",  # minute zero-padded
            "%-M": "Minute", # minute decimal
            "%S": "Second",  # second zero-padded
            "%-S": "Second", # second decimal
            "%p": "AM_PM",   # AM/PM
        }

        # given alphanumeric token in date_str, finds all possible specifiers it could correspond to
        token_to_specifier = dict()
        for specifier in specifiers:
            token = date.strftime(specifier)
            token_to_specifier[token.lower()] = token_to_specifier.get(token, []) + [specifier]

        # breaks original date_str down into tokens and delimiters
        token_delimiter_arr = re.compile(r"([a-zA-Z0-9]+)|([^a-zA-Z0-9]+)").findall(date_str)
        
        # matches possible specifiers for each token
        specifiers_for_each_token = []
        for (token, delimiter) in token_delimiter_arr:  # exactly one of each tuple will be None
            if token:
                if token.lower() in token_to_specifier:
                    specifiers_for_each_token.append(token_to_specifier[token.lower()])
                else:  # no match for token, just append literal
                    specifiers_for_each_token.append([token])
            else:
                specifiers_for_each_token.append([delimiter])

        # generates list of possible specifier arrays (cartesian product)
        specifier_arrays = itertools.product(*specifiers_for_each_token)

        # filtering list to remove cases where there are duplicate specifier types within one specifier array
        valid_specifier_strs = []
        valid_specifier_types = []  # may be useful for determining graph to plot (which values are meaningful in the datetime)
        for specifier_array in specifier_arrays:
            valid_specifier_array = True
            used_specifier_types = set()
            for specifier in specifier_array:
                if specifier not in specifiers:  # is a delimiter
                    continue
                specifier_type = specifiers[specifier]
                if specifier_type in used_specifier_types:
                    valid_specifier_array = False
                    break
                used_specifier_types.add(specifier_type)
            if valid_specifier_array:
                valid_specifier_strs.append("".join(specifier_array))
                valid_specifier_types.append(used_specifier_types)

        return (valid_specifier_strs, valid_specifier_types)

    ############################################################################
    # returns (norm_records)
    def normalize_ordinal(self, header, records):
        norm_records = []
        for record in records:
            if record.lower() in self.ordinal_normalizer_dict:
                norm_records.append(self.ordinal_normalizer_dict[record.lower()])
            else:
                try:
                    norm_records.append(int(float(record.replace(",", "").replace(" ", ""))))
                except ValueError:
                    norm_records.append(record)
        return norm_records

    ############################################################################
    # returns (norm_records, vega_lite_timeunit)
    def normalize_temporal(self, header, records):
        # finding most common date format applicable throughout list of records
        date_formats_arr = [self.find_candidate_date_formats(record) for record in records]
        date_formats_used = dict()
        date_formats_to_specifier_types = dict()
        for (date_formats, specifier_types) in date_formats_arr:
            for i in range(len(date_formats)):
                date_formats_used[date_formats[i]] = date_formats_used.get(date_formats[i], 0) + 1
                date_formats_to_specifier_types[date_formats[i]] = specifier_types[i]
        if len(date_formats_used) == 0:  # no candidate date formats throughout records
            return (records, None)
        sorted_date_formats = [x[0] for x in sorted(date_formats_used.items(), key=lambda x: x[1], reverse=True)]

        # based on the most common set of specifier types in records, choose a format to normalize the original list of records into (one recognizable by vega-lite)
        # set vega_lite_timeunit accordingly (https://vega.github.io/vega-lite/docs/timeunit.html)
        best_specifier_types = date_formats_to_specifier_types[sorted_date_formats[0]]
        if best_specifier_types == {"Year",}:
            best_normalized_format = "%Y"
            vega_lite_timeunit = "year"
        elif best_specifier_types == {"Year", "Month"}:
            best_normalized_format = "%b %Y"
            vega_lite_timeunit = "yearmonth"
        elif best_specifier_types == {"Year", "Month", "Day"}:
            best_normalized_format = "%b %-d %Y"
            vega_lite_timeunit = "yearmonthdate"
        elif best_specifier_types == {"Year", "Month", "Day", "Hour"}:
            best_normalized_format = "%b %-d %H %Y"
            vega_lite_timeunit = "yearmonthdatehours"
        elif best_specifier_types == {"Year", "Month", "Day", "Hour", "Minute"}:
            best_normalized_format = "%b %-d %H:%M %Y"
            vega_lite_timeunit = "yearmonthdatehoursminutes"
        elif best_specifier_types == {"Year", "Month", "Day", "Hour", "Minute", "Second"}:
            best_normalized_format = "%b %-d %H:%M:%S %Y"
            vega_lite_timeunit = "yearmonthdatehoursminutesseconds"
        elif best_specifier_types == {"Month",}:
            best_normalized_format = "%b"
            vega_lite_timeunit = "month"
        elif best_specifier_types == {"Month", "Day"}:
            best_normalized_format = "%b %-d"
            vega_lite_timeunit = "monthdate"
        elif best_specifier_types == {"Weekday",}:
            best_normalized_format = "%a"
            vega_lite_timeunit = "day"
        elif best_specifier_types == {"Hour", "Minute"}:
            best_normalized_format = "%H:%M"
            vega_lite_timeunit = "hoursminutes"
        elif best_specifier_types == {"Hour", "Minute", "Second"}:
            best_normalized_format = "%H:%M:%S"
            vega_lite_timeunit = "hoursminutesseconds"
        else:  # some other weird combination of specifier types that is very unconventional, do not normalize
            return (records, None)

        # normalizing records, taking precedence of date formats based on order in sorted_date_formats
        norm_records = []
        for record_idx in range(len(records)):
            if date_formats_arr[record_idx] == ([], []):  # cannot be parsed
                norm_records.append(records[record_idx])
                continue
            for date_format in sorted_date_formats:  # precedence
                if date_format in date_formats_arr[record_idx][0]:  # current record can be read in that format
                    unpadded_date_format = date_format.replace("%-", "%")
                    dt = datetime.datetime.strptime(records[record_idx], unpadded_date_format)
                    norm_records.append(dt.strftime(best_normalized_format))
                    break

        return (norm_records, vega_lite_timeunit)

    ############################################################################
    # returns (norm_records_starts, norm_records_ends, vega_lite_timeunit)
    def normalize_temporal_range(self, header, records):
        return (records, records, "")

    ############################################################################
    # returns (norm_records, units)
    def normalize_money(self, header, records):
        norm_records = []
        for record in records:
            try:
                norm_records.append(float(record.replace("$", "").replace(",", "")))
            except ValueError:
                if record == "":  # this assumes that an empty string means 0
                    norm_records.append(0)
                else:
                    norm_records.append(record)
        return (norm_records, "")

    ############################################################################
    # returns (norm_records)
    def normalize_percent(self, header, records):
        norm_records = []
        for record in records:
            try:
                norm_records.append(float(record.replace("%", "")))
            except ValueError:
                if record == "":  # this assumes that an empty string means 0
                    norm_records.append(0)
                else:
                    norm_records.append(record)
        return norm_records

    ############################################################################
    # returns (norm_records, units)
    def normalize_quant_units(self, header, records):
        return (records, "")

    ############################################################################
    # returns (norm_records)
    def normalize_quant_default(self, header, records):
        norm_records = []
        for record in records:
            try:
                norm_records.append(int(float(record.replace(",", "").replace(" ", ""))))
            except ValueError:
                if record == "":  # this assumes that an empty string means 0
                    norm_records.append(0)
                else:
                    norm_records.append(record)
        return norm_records

    ############################################################################
    # returns (norm_records_starts, norm_records_ends)
    def normalize_quant_range(self, header, records):
        return (records, records)

    ############################################################################
    # returns (norm_records)
    def normalize_default(self, header, records):
        return records
