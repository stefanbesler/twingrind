import os
import logging
import pyads
import pickle
import ctypes
from pytwingrind import common

def run(netid: str, port: int, directory: str):
  callstacks = []
  logging.info(f"Connecting {netid}:{port}")
  if netid == "":
    pyads.ads.open_port()
    netid = pyads.ads.get_local_address().netid
    pyads.ads.close_port()
  
  plc = pyads.Connection(netid, port)
  try:
    plc.open()
    
    # get header data
    tasks = plc.read_by_name('Profiler.Tasks', pyads.PLCTYPE_SINT)
    max_stacksize = plc.read_by_name('ParameterList.MAX_STACKSIZE', pyads.PLCTYPE_DINT)     
    frames = plc.read_by_name('Profiler.FrameIndex', pyads.PLCTYPE_BYTE)
    
    logging.info(f"""Fetching callstacks from PLC with
    max_stacksize = {max_stacksize}        
    tasks = {tasks}
    frames = {frames}""")

    common.create_stack_class(max_stacksize)
    
    for task in range(1, tasks+1):

        cycletime = plc.read_by_name(f"Profiler.CycleTime[{task}]", pyads.PLCTYPE_UDINT)
    
        for frame in range(frames):
          stacksize = plc.read_by_name(f"Profiler.Stacks[{frame}]", pyads.PLCTYPE_DINT)

          # abort if we don't get a valid stack out of it
          if stacksize == 0:
            continue
            
          stack = plc.read_by_name(f"Profiler.Frames[{frame}, {task}]", common.Stack)
          path = os.path.join(directory, f"callstack_frame_{frame}_task_{task}")
          callstacks.append(path)
          pickle.dump(common.Callstack(cycletime=cycletime, task=task, max_stacksize=max_stacksize, stack=stack), open(callstacks[-1], "wb"))
          logging.info(f"Fetched Callstack {frame} (Task {task}) with calls {int(stacksize/2)} to {path}")

  except pyads.ADSError as e:
      logging.error(e)
  finally:
      plc.close()
      
  return callstacks


