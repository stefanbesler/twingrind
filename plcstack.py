import ctypes

class Call(ctypes.Structure):
    _fields_ = [("hash", ctypes.c_int),
                ("depth", ctypes.c_int),
                ("startlo", ctypes.c_longlong),
                ("starthi", ctypes.c_longlong),
                ("endlo", ctypes.c_longlong),
                ("endhi", ctypes.c_longlong)]


def create_hash(fb, method, hashes):
    increment = 0

    # todo find a better way to create a hash, if we ever exceed the 65000 we get into trouble
    while True:
        hstr = fb + "::" + method + str(increment)
        h = hash(hstr) & 65535
        if h not in hashes:
            hashes[h] = (fb, method)
            return h
        increment += 1