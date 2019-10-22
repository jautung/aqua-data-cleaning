import num2words
import re
import itertools
import dateutil.parser
import datetime
import pint

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
        except:  # unable to parse date_str as a date in the first place
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

    # auxiliary function
    # based on the most common set of specifier types in records, choose a format to normalize the original list of records into (one recognizable by vega-lite)
    # set vega_lite_timeunit accordingly (https://vega.github.io/vega-lite/docs/timeunit.html)
    def choose_temporal_format(self, best_specifier_types):
        best_normalized_format = None
        vega_lite_timeunit = None
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
        return (best_normalized_format, vega_lite_timeunit)

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

        best_specifier_types = date_formats_to_specifier_types[sorted_date_formats[0]]
        (best_normalized_format, vega_lite_timeunit) = self.choose_temporal_format(best_specifier_types)
        if best_normalized_format == None: # some other weird combination of specifier types that is very unconventional, do not normalize
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
        # splitting the range
        records_start = []
        records_end = []
        for record in records:
            if record.count("-") == 1:
                (start, end) = record.split("-")
                records_start.append(start.strip())
                records_end.append(end.strip())
            else:
                records_start.append(record)
                records_end.append(None)

        # finding most common date format applicable throughout list of records
        date_formats_arr_start = [self.find_candidate_date_formats(record) for record in records_start]
        date_formats_arr_end = [self.find_candidate_date_formats(record) for record in records_end]
        date_formats_used = dict()
        date_formats_to_specifier_types = dict()
        for (date_formats, specifier_types) in (date_formats_arr_start + date_formats_arr_end):
            for i in range(len(date_formats)):
                date_formats_used[date_formats[i]] = date_formats_used.get(date_formats[i], 0) + 1
                date_formats_to_specifier_types[date_formats[i]] = specifier_types[i]
        if len(date_formats_used) == 0:  # no candidate date formats throughout records
            return (records, [], None)
        sorted_date_formats = [x[0] for x in sorted(date_formats_used.items(), key=lambda x: x[1], reverse=True)]

        best_specifier_types = date_formats_to_specifier_types[sorted_date_formats[0]]
        (best_normalized_format, vega_lite_timeunit) = self.choose_temporal_format(best_specifier_types)
        if best_normalized_format == None: # some other weird combination of specifier types that is very unconventional, do not normalize
            return (records, [], None)

        # normalizing records, taking precedence of date formats based on order in sorted_date_formats
        norm_records_starts = []
        norm_records_ends = []
        for record_idx in range(len(records)):
            start_done = False
            end_done = False
            if date_formats_arr_start[record_idx] == ([], []):  # cannot be parsed
                norm_records_starts.append(records_start[record_idx])
                start_done = True
            if date_formats_arr_end[record_idx] == ([], []):  # cannot be parsed
                norm_records_ends.append(records_end[record_idx])
                end_done = True
            if not start_done or not end_done:
                for date_format in sorted_date_formats:  # precedence
                    if not start_done and date_format in date_formats_arr_start[record_idx][0]:  # current record can be read in that format
                        unpadded_date_format = date_format.replace("%-", "%")
                        dt = datetime.datetime.strptime(records_start[record_idx], unpadded_date_format)
                        norm_records_starts.append(dt.strftime(best_normalized_format))
                        start_done = True
                    if not end_done and date_format in date_formats_arr_end[record_idx][0]:  # current record can be read in that format
                        unpadded_date_format = date_format.replace("%-", "%")
                        dt = datetime.datetime.strptime(records_end[record_idx], unpadded_date_format)
                        norm_records_ends.append(dt.strftime(best_normalized_format))
                        end_done = True
                    if start_done and end_done:
                        break

        return (norm_records_starts, norm_records_ends, vega_lite_timeunit)

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
        most_common_currencies = ["usd", "eur", "jpy", "gbp", "aud", "cad", "chf", "cny", "hkd", "nzd"]
        currency = None
        for curr in most_common_currencies:
            if curr in header.lower():
                currency = curr
                break
        return (norm_records, currency)

    ############################################################################
    # returns (norm_records)
    def normalize_percent(self, header, records):
        norm_records = []
        num_above_one = 0  # to determine if this is given as decimal or percentage
        num_below_one = 0
        for record in records:
            try:
                val = float(record.replace("%", ""))
            except ValueError:
                if record == "":  # this assumes that an empty string means 0
                    norm_records.append(0)
                else:
                    norm_records.append(record)
            else:
                norm_records.append(val)
                if val > 1:
                    num_above_one += 1
                else:
                    num_below_one += 1
        if num_below_one > num_above_one:
            return [record * 100 for record in norm_records]  # decimal to percentage
        else:
            return norm_records

    ############################################################################
    # returns (norm_records, units)
    def normalize_quant_units(self, header, records):
        ureg = pint.UnitRegistry()
        norm_records = []
        freq_of_units = dict()
        for record in records:
            try:
                quant = ureg.parse_expression(record)
            except:  # would like to give exact errors here but there are far too many to handle
                norm_records.append(record)
            else:
                if isinstance(quant, int) or isinstance(quant, float):  # already a number, no units
                    norm_records.append(quant)
                else:
                    norm_records.append(quant.magnitude)
                    freq_of_units[quant.units] = freq_of_units.get(quant.units, 0) + 1
        if len(freq_of_units) > 0:  # most common unit among records
            ret_units = str(sorted(freq_of_units.items(), key=lambda x: x[1], reverse=True)[0][0])
        else:
            ret_units = header.replace("\n", " ").split(" ")[-1].replace("(", "").replace(")", "").replace("[", "").replace("]", "")  # hopefully the header contains the unit
        return (norm_records, ret_units)

    ############################################################################
    # returns (norm_records)
    def normalize_quant_default(self, header, records):
        norm_records = []
        for record in records:
            try:
                record_float = float(record.replace(",", "").replace(" ", ""))
            except ValueError:
                if record == "":  # this assumes that an empty string means 0
                    norm_records.append(0)
                else:
                    norm_records.append(record)
            else:
                if record_float.is_integer():
                    norm_records.append(int(record_float))
                else:
                    norm_records.append(record_float)
        return norm_records

    ############################################################################
    # returns (norm_records_starts, norm_records_ends)
    def normalize_quant_range(self, header, records):
        # splitting the range
        records_start = []
        records_end = []
        for record in records:
            if record.count("-") == 1:
                (start, end) = record.split("-")
                records_start.append(start.strip())
                records_end.append(end.strip())
            else:
                records_start.append(record)
                records_end.append("")

        return (self.normalize_quant_default(header, records_start), self.normalize_quant_default(header, records_end))

    ############################################################################
    # returns (norm_records)
    def normalize_default(self, header, records):
        return records
