import pandas as pd

def convert_repeating(data, index):
    """Takes a data series and converts it to match the freq of index.

    For conversions to higher freq, it fills forward the series given.

    Not implemented: For conversions to a lower freq, it takes the mean of the series given.
    """
    if isinstance(data, (int, float)):
        return pd.Series(data, index=index)
    new_freq = data.asfreq(index.freq, how = "S")
    index_union = pd.Index.union(new_freq.index, index)
    old_and_new_index = new_freq.reindex(index_union, method="ffill")
    new_index_only = old_and_new_index.reindex(index)
    return new_index_only

def convert_one_time(data, index):
    if data.index.freq == index.freq:
        return data
    if is_higher_freq(data.index, index):
        return _convert_one_time_higher(data, index)
    return _convert_one_time_lower(data, index)

def _convert_one_time_higher(data, index):
    """Converts data to the series of index, with no filling.

    For conversions to higher frequency, the data is divided uniformly
    across the periods.

    For conversions to lower frequency, the data is summed for the periods.
    """
    #Count num periods in index.
    new_freq = data.asfreq(index.freq, how="S")
    periods_count = (data
                     .resample(index.freq)
                     .pad()
                     .asfreq(data.index.freq)
                     .index
                     .value_counts())
    divided = new_freq.asfreq(data.index.freq) / periods_count
    return divided.asfreq(index.freq, how="S").reindex(index, method="ffill")

def _convert_one_time_lower(data, index):
    return data.resample(index.freq).sum()


def is_higher_freq(index1, index2):
    return length_period(index1[0]) > length_period(index2[0])

def length_period(freq):
    return freq.end_time - freq.start_time
    
