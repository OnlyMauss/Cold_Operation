# id_gen.py
_counter = [1]


def next_id():
    v = _counter[0]
    _counter[0] += 1
    return v