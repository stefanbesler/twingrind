import ctypes
import chardet
import os
import re
from dataclasses import dataclass

profiler_tag = r"(* @@ PROFILER @@ *)"

@dataclass
class GuardExclusionToken:
    token: str
    description: str

file_skip_tokens = [
    GuardExclusionToken(profiler_tag, "Guards already present"),
    GuardExclusionToken('<SFC>', "Sequential function chart detected (SFC)"),
    GuardExclusionToken('<NWL>', "Ladder Logic Diagram detected (LD)"),
    GuardExclusionToken('<CFC', "Continuous Function Chart detected (CFC)"),
    GuardExclusionToken('<StateChart>', "Sequential function chart detected (SC)"),
    ]

def detect_encoding(filepath : str):
  
    with open(filepath, 'rb') as f:
      result = chardet.detect(f.read())
      return result['encoding']
    
    return 'utf-8'

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
                
def create_stack_class(size : int):
    # create global class to keep pickle happy
    global Stack
    class Stack(ctypes.Structure):
        _fields_ = [("calls", Call * (size))]
                
class Callstack(object):
    def __init__(self, cycletime : int, task : int, size : int, stack : ctypes.Structure):
        self.cycletime = cycletime
        self.task = task
        self.size = size
        self.stack = stack
