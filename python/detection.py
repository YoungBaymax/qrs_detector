import numpy as np

_WINDOW_SEC = 0.150
_MIN_RR = 0.2


def detect(signal, rate):
    filtered = _low_pass_filter(signal)
    filtered = _high_pass_filter(filtered)
    squared_derivative = _squared_derivative(filtered)
    samples_window = round(_WINDOW_SEC * rate)
    integrated = _window_integration(squared_derivative, samples_window)

    # In the paper delay is 6 samples for LPF and 16 samples for HPF
    # with sampling rate equals 200
    delay_sec = (6 + 16) / 200.0
    # delay_sec += _WINDOW_SEC / 2.0
    offset = round(delay_sec * rate)

    indices = _new_thresholding(integrated, round(_MIN_RR * rate))
    indices = [x - offset for x in indices]
    return indices


def _low_pass_filter(signal):
    result = []
    for index, value in enumerate(signal):
        if index >= 1:
            value += 2 * result[index - 1]
        if index >= 2:
            value -= result[index - 2]
        if index >= 6:
            value -= 2 * signal[index - 6]
        if index >= 12:
            value += signal[index - 12]
        result.append(value)
    return result


def _high_pass_filter(signal):
    result = []
    for index, value in enumerate(signal):
        value = -value
        if index >= 1:
            value -= result[index - 1]
        if index >= 16:
            value += 32 * signal[index - 16]
        if index >= 32:
            value += signal[index - 32]
        result.append(value)
    return result


def _squared_derivative(signal):
    result = []
    for index in range(2, len(signal) - 2):
        value = (signal[index + 2] + 2 * signal[index + 1] -
                 signal[index - 2] - 2 * signal[index - 1])
        value /= 8.0
        result.append(value * value)
    return result


def _window_integration(signal, window_size):
    result = []
    value = 0
    for i, x in enumerate(signal):
        first = i - (window_size - 1)
        value += x / window_size
        if first > 0:
            value -= signal[first - 1] / window_size
        result.append(value)
    return result


def _thresholding(integrated, min_rr_samples):
    spki = 0
    npki = 0
    peaks = [0]
    threshold1 = spki
    for i in range(1, len(integrated) - 1):
        peaki = integrated[i]
        if peaki < integrated[i - 1] or peaki < integrated[i + 1]:
            continue

        if peaki <= threshold1:
            npki = 0.875 * npki + 0.125 * peaki
        else:
            spki = 0.875 * spki + 0.125 * peaki

        threshold1 = npki + 0.25 * (spki - npki)
        # threshold2 = 0.5 * threshold1

        if peaki > threshold1 and i - peaks[-1] >= min_rr_samples:
            peaks.append(i)
        # TODO: correct first
    return peaks[1:]


def _find_local_max(values):
    peak_index = None
    for index in range(1, len(values) - 1):
        value = values[index]
        if value < values[index - 1] or value < values[index + 1]:
            continue
        if peak_index is None or value > values[peak_index]:
            peak_index = index
    return peak_index


def _new_thresholding(integrated, min_rr_samples):
    peak_indicies = _find_peaks(integrated, limit=0.35, spacing=min_rr_samples)
    # peak_indicies = _find_peaks_(integrated, limit=0.35, spacing=min_rr_samples)
    spki = 0
    npki = 0
    peaks = []
    last_peak = 0
    threshold = 0
    for index in peak_indicies:
        if last_peak > 0 and index - last_peak < min_rr_samples:
            continue
        value = integrated[index]
        if value < threshold:
            npki = 0.875 * npki + 0.125 * value
        else:
            peaks.append(index)
            spki = 0.875 * spki + 0.125 * value
            last_peak = index
        threshold = npki + 0.25 * (spki - npki)
    return peaks


def _find_peaks(data, spacing=1, limit=None):
    """
    Finds peaks in `data` which are of `spacing` width and >=`limit`.
    :param ndarray data: data
    :param float spacing: minimum spacing to the next peak (should be 1 or more)
    :param float limit: peaks should have value greater or equal
    :return array: detected peaks indexes array
    """
    data = np.array(data)
    size = data.size
    x = np.zeros(size + 2 * spacing)
    x[:spacing] = data[0] - 1.e-6
    x[-spacing:] = data[-1] - 1.e-6
    x[spacing:spacing + size] = data
    peak_candidate = np.zeros(size)
    peak_candidate[:] = True
    for s in range(spacing):
        start = spacing - s - 1
        h_b = x[start: start + size]  # before
        start = spacing
        h_c = x[start: start + size]  # central
        start = spacing + s + 1
        h_a = x[start: start + size]  # after
        peak_candidate = np.logical_and(peak_candidate,
                                        np.logical_and(h_c > h_b, h_c > h_a))
    ind = np.argwhere(peak_candidate)
    ind = ind.reshape(ind.size)
    if limit is not None:
        ind = ind[data[ind] > limit]
    return ind


def _find_peaks_(data, spacing, limit):
    size = len(data)
    x = [data[0] - 1.0e-6 for _ in range(spacing)]
    x += data
    x += [data[-1] - 1.0e-6 for _ in range(spacing)]
    candidate = [True for _ in range(size)]
    for s in range(spacing):
        start = spacing - s - 1
        h_before = x[start:(start + size)]
        start = spacing
        h_central = x[start:(start + size)]
        start = spacing + s + 1
        h_after = x[start:(start + size)]
        candidate = _lists_and(candidate, _lists_and(_lists_greater(h_central, h_before), _lists_greater(h_central, h_after)))
    return [i for i, x in enumerate(candidate) if x and data[i] > limit]


def _lists_and(left, right):
    size = len(left)
    return [left[i] and right[i] for i in range(size)]


def _lists_greater(left, right):
    size = len(left)
    return [left[i] > right[i] for i in range(size)]
