import os
import re
import logging
import time
import datetime
from argparse import ArgumentParser
import pyads
import ctypes
import pickle
from plcstack import Call

parser = ArgumentParser("""triggers the measurement of a single profile and
stores the corresponding callstack on disk""")

parser.add_argument("-n", "--netid", help="netid of the target machine", default="")
parser.add_argument("-p", "--port", help="port of the plc", default=851)
parser.add_argument("-d", "--dest", help="output directory ", default="./")
args = vars(parser.parse_args())

logging.basicConfig(level=logging.DEBUG)
netid = args['netid']
port = int(args['port'])
dest = args['dest']

plc = pyads.Connection(netid, port)
try:
  logging.debug('connecting {}:{}'.format(netid, port))

  plc.open()

  logging.debug('Reading')
  frames = plc.read_by_name('Profiler.FrameIndex', pyads.PLCTYPE_BYTE)
  
  for i in range(frames):
    stacksize = plc.read_by_name('Profiler.Stacks[{}]'.format(i), pyads.PLCTYPE_DINT)

    logging.debug('Frame {}: stacksize {}'.format(i, int((stacksize))))

    # abort if we don't get a valid stack out of it
    if stacksize == 0:
      continue

    # maybe a TC3 breakpoint is active, or plc crashed?
    if plc.read_by_name('Profiler.Busy', pyads.PLCTYPE_BOOL):
      raise Exception('''Profiler still working, breakpoint active?''')

    # define a new stack class that can contain as many calls as were
    # actually performed - yes, we can do that with python :)
    class Stack(ctypes.Structure):
      _fields_ = [("calls", Call * (stacksize))]

    stack = plc.read_by_name('Profiler.Frames[{}]'.format(i), Stack)
    pickle.dump(stack, open(os.path.join(dest, "callstack_frame_{}".format(i)), "wb"))

except pyads.ADSError as e:
    logging.error(e)
finally:
    plc.close()


