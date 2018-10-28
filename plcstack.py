import ctypes

class Call(ctypes.Structure):
    _fields_ = [("hash", ctypes.c_int),
                ("depth", ctypes.c_int),
                ("startlo", ctypes.c_longlong),
                ("starthi", ctypes.c_longlong),
                ("endlo", ctypes.c_longlong),
                ("endhi", ctypes.c_longlong)]