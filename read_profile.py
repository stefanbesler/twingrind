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

parser.add_argument("-n", "--netid", help="netid of the target machine")
parser.add_argument("-p", "--port", help="port of the plc", default=851)
parser.add_argument("-d", "--dest", help="output directory ", default="./")
parser.add_argument("-r", "--notrigger", help="if set, the script won't trigger, but simply read old data", action="store_true")
args = vars(parser.parse_args())

logging.basicConfig(level=logging.DEBUG)
netid = args['netid']
port = int(args['port'])
dest = args['dest']
trigger = not args['notrigger']

plc = pyads.Connection(netid, port)
try:
    logging.debug('connecting {}:{}'.format(netid, port))

    plc.open()

    if trigger:
        logging.debug('trigger measurement')
        plc.write_by_name('Global.profilerdata.stacksize', 0, pyads.PLCTYPE_DINT)
        time.sleep(1) # no need, but lets be sure
        plc.write_by_name('Global.profilerdata.enabled', True, pyads.PLCTYPE_BOOL)

        # wait (we dont really have to since 1 ads call should take at least
        # 1 cycle of the plc anyway, but lets be sure ...
        time.sleep(3)

    logging.debug('reading measurement')
    stacksize = plc.read_by_name('Global.profilerdata.stacksize', pyads.PLCTYPE_DINT)

    logging.debug('  -> {} methods were called'.format(int((stacksize-1)/2)))

    # abort if we don't get a valid stack out of it
    if stacksize == 0:
        raise Exception('''no methods were called, check if setDataRef for Profiler got called and/or 
                           # actual called methods > max_stacksize (see parameter in Twincat3 Library''')

    # maybe a TC3 breakpoint is active, or plc crashed?
    if plc.read_by_name('Global.profilerdata.enabled', pyads.PLCTYPE_BOOL):
        raise Exception('''profiler still working, breakpoint active?''')

    # define a new stack class that can contain as many calls as were
    # actually performed - yes, we can do that with python :)
    class Stack(ctypes.Structure):
        _fields_ = [("calls", Call * (stacksize+1))]

    stack = plc.read_by_name('Global.profilerdata.stack', Stack)

    logging.debug('store measurement')
    pickle.dump(stack, open(os.path.join(dest, "callstack_{}".format(datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))), "wb"))

except pyads.ADSError as e:
    logging.error(e)
finally:
    plc.close()


