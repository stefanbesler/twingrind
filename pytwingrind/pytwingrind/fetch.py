import os
import time
import logging
import pyads
import pickle
import ctypes
from pytwingrind import common

def trigger_edge(plc, symbol: str, pause_duration: float):
  plc.write_by_name(symbol, True, pyads.PLCTYPE_BOOL)
  time.sleep(pause_duration)
  plc.write_by_name(symbol, False, pyads.PLCTYPE_BOOL)
  time.sleep(pause_duration)  

def run(netid: str, port: int, directory: str, outputname: str, namespace: str, reset: bool, shots: int):
  profiler_symbolname = "Profiler"
  parameterlist_symbolname = "ParameterList"
  
  callstacks = []
  is_capturing = False
  logging.info(f"Connecting {netid}:{port}")
  if netid == "":
    pyads.ads.open_port()
    netid = pyads.ads.get_local_address().netid
    pyads.ads.close_port()
  
  plc = pyads.Connection(netid, port)
  try:
    plc.open()
    
    for i in range(0, 2):
      logging.debug(f"Trying to connect to profiler at {profiler_symbolname}")
      try:
        plc.read_by_name(f"{profiler_symbolname}.CaptureContinuous", pyads.PLCTYPE_BOOL)
      except Exception as e:
        if i == 0:
          profiler_symbolname = ".".join(filter(None, [namespace, "Profiler"]))
          parameterlist_symbolname = ".".join(filter(None, [namespace, "ParameterList"]))
        else:
          raise Exception(f"Could not resolve entry point for profiler, make sure you PLC running and the Profiler symbol is available at 'Profiler' or '{namespace}.Profiler'")
    
    # get header data
    tasks = plc.read_by_name(f"{profiler_symbolname}.Tasks", pyads.PLCTYPE_SINT)
    is_capturing = plc.read_by_name(f"{profiler_symbolname}.CaptureContinuous", pyads.PLCTYPE_BOOL)
    capturing_mode = plc.read_by_name(f"{profiler_symbolname}.Mode", pyads.PLCTYPE_INT)
    low_threshold = plc.read_by_name(f"{profiler_symbolname}.CaptureCpuTimeLowThreshold", pyads.PLCTYPE_LREAL)
    high_threshold = plc.read_by_name(f"{profiler_symbolname}.CaptureCpuTimeHighThreshold", pyads.PLCTYPE_LREAL)    
    max_cycletime_in_s = max([plc.read_by_name(f"{profiler_symbolname}.CycleTime[{task}]", pyads.PLCTYPE_UDINT) for task in range(1, tasks+1)]) / 10000000.0
    pause_duration = 5 * max_cycletime_in_s
          
    # stop capturing
    if is_capturing:
      plc.write_by_name(f"{profiler_symbolname}.CaptureOnce", False, pyads.PLCTYPE_BOOL)
      logging.info(f"Capturing paused")
      
    # optionally reset previously taken frames
    if reset:  
      logging.debug(f"Resetting profiler")
      trigger_edge(plc, f"{profiler_symbolname}.Reset", pause_duration)
        
    # optionally capture some frames
    if shots > 0:
      logging.debug(f"Temporarily configuring profiler for taking singleshots")
      plc.write_by_name(f"{profiler_symbolname}.Mode", 0, pyads.PLCTYPE_INT)
      plc.write_by_name(f"{profiler_symbolname}.CaptureCpuTimeLowThreshold", 0, pyads.PLCTYPE_LREAL)
      plc.write_by_name(f"{profiler_symbolname}.CaptureCpuTimeHighThreshold", 0, pyads.PLCTYPE_LREAL)
      
      for i in range(shots):
        logging.info(f"Taking snapshot {i+1}/{shots}")
        trigger_edge(plc, f"{profiler_symbolname}.CaptureOnce", pause_duration)        

    time.sleep(pause_duration);
    
    # read all the data that the profile already captured
    max_stacksize = plc.read_by_name(f"{parameterlist_symbolname}.MAX_STACKSIZE", pyads.PLCTYPE_DINT)
    max_frames = plc.read_by_name(f"{parameterlist_symbolname}.MAX_FRAMES", pyads.PLCTYPE_SINT)  
    frameIndex = plc.read_by_name(f"{profiler_symbolname}.FrameIndex", pyads.PLCTYPE_BYTE)

    logging.info(f"""Fetching callstacks from PLC with
    entrypoint = {profiler_symbolname}                 
    max_stacksize = {max_stacksize}
    max_frames = {max_frames}
    max_cycletime (s) = {max_cycletime_in_s}
    tasks = {tasks}""")    
    
    common.create_stack_class(max_stacksize)
    counter = 0
    for task in range(1, tasks+1):
        cycletime = plc.read_by_name(f"{profiler_symbolname}.CycleTime[{task}]", pyads.PLCTYPE_UDINT)
    
        for frame in range(max_frames):
          stacksize = plc.read_by_name(f"{profiler_symbolname}.Meta[{frame}].Size", pyads.PLCTYPE_DINT)

          # abort if we don't get a valid stack out of it
          if stacksize > 0 and frame != frameIndex:            
            stack = plc.read_by_name(f"{profiler_symbolname}.Data[{frame},{task}]", common.Stack)
            path = os.path.join(directory, f"{outputname}_frame_{counter}_task_{task}")
            callstacks.append(path)
            pickle.dump(common.Callstack(cycletime=cycletime, task=task, size=stacksize, stack=stack), open(callstacks[-1], "wb"))
            logging.info(f"Fetched Callstack {counter} (Task {task}) with calls {int(stacksize/2)} to {path}")
            counter += 1

  except pyads.ADSError as e:
    logging.error(e)
  finally:
    try:
      logging.debug(f"Reconfiguring profiler to initial setup")
      plc.write_by_name(f"{profiler_symbolname}.Mode", capturing_mode, pyads.PLCTYPE_INT)
      plc.write_by_name(f"{profiler_symbolname}.CaptureCpuTimeLowThreshold", low_threshold, pyads.PLCTYPE_LREAL)
      plc.write_by_name(f"{profiler_symbolname}.CaptureCpuTimeHighThreshold", high_threshold, pyads.PLCTYPE_LREAL) 
      plc.write_by_name(f"{profiler_symbolname}.CaptureContinuous", is_capturing, pyads.PLCTYPE_BOOL)        
    except:
      pass
    plc.close()
      
  return callstacks


