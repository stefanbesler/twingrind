import os
import logging
import pyads
import pickle
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

    
    # maybe a TC3 breakpoint is active, or plc crashed?
    if plc.read_by_name('Profiler.Busy', pyads.PLCTYPE_BOOL):
      raise Exception('''Profiler still working, breakpoint active?''')    
    
    frames = plc.read_by_name('Profiler.FrameIndex', pyads.PLCTYPE_BYTE)
    for i in range(frames):
      stacksize = plc.read_by_name('Profiler.Stacks[{}]'.format(i), pyads.PLCTYPE_DINT)

      logging.info('Found Frame {} with stacksize {}'.format(i, int((stacksize))))

      # abort if we don't get a valid stack out of it
      if stacksize == 0:
        continue
        
      stack = plc.read_by_name('Profiler.Frames[{}]'.format(i), common.Stack)
      callstacks.append(os.path.join(directory, "callstack_frame_{}".format(i)))
      pickle.dump(stack, open(callstacks[-1], "wb"))

  except pyads.ADSError as e:
      logging.error(e)
  finally:
      plc.close()
      
  return callstacks


