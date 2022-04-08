import ctypes

class Call(ctypes.Structure):
    _fields_ = [("hash", ctypes.c_uint32),
                ("depth", ctypes.c_int32),
                ("startlo", ctypes.c_uint32),
                ("starthi", ctypes.c_uint32),
                ("endlo", ctypes.c_uint32),
                ("endhi", ctypes.c_uint32)]
