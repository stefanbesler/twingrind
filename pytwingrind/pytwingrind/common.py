import ctypes
profiler_tag = r"(* @@ PROFILER @@ *)"

def find_sourcefiles(filepath : str):
    """walk recursively through folders and look for TwinCat3 source files"""

    for subdir, _, files in os.walk(filepath):
        for f in files:
            re_source = re.match(".*.tcpou$", f, re.I) 
            if re_source:
                yield os.path.join(subdir, f)

class Call(ctypes.Structure):
    _fields_ = [("hash", ctypes.c_uint32),
                ("depth", ctypes.c_int32),
                ("startlo", ctypes.c_uint32),
                ("starthi", ctypes.c_uint32),
                ("endlo", ctypes.c_uint32),
                ("endhi", ctypes.c_uint32)]

class Stack(ctypes.Structure):
    _fields_ = [("calls", Call * (320000))]