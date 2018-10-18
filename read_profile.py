import os
import re
import logging
import time
import datetime
from argparse import ArgumentParser
import pyads
import ctypes
import pickle

class Call(ctypes.Structure):
    _fields_ = [("fb_name", ctypes.c_byte * 81),
                ("method_name", ctypes.c_byte * 81),
                ("depth", ctypes.c_int),
                ("startlo", ctypes.c_int),
                ("starthi", ctypes.c_int),
                ("endlo", ctypes.c_int),
                ("endhi", ctypes.c_int)]

parser = ArgumentParser("""triggers the measurement of a single profile and
stores the corresponding callstack on disk""")

parser.add_argument("-n", "--netid", help="netid of the target machine", required=False)
parser.add_argument("-p", "--port", help="port of the plc", default=851, required=False)
parser.add_argument("-d", "--dest", help="output directory ", default="./", required=False)
parser.add_argument("-n", "--notrigger", help="if set, the script won't trigger, but simply"\
                    "read the last available data from the plc", action="store_true")
args = vars(parser.parse_args())

logging.basicConfig(level=logging.DEBUG)
netid = args['netid']
port = args['port']
dest = args['dest']
trigger = not args['notrigger']

try:
    logging.debug('connecting {}:{}'.format(netid, port))

    plc = pyads.Connection(netid, port)
    plc.open()

    if trigger:
        logging.debug('trigger measurement')
        plc.write_by_name('Global.profiler.disabled', False, pyads.bool)

    # wait (we dont really have to since 1 ads call should take at least
    # 1 cycle of the plc anyway, but lets be sure ...
    time.sleep(1)

    logging.debug('reading measurement')
    nstack = plc.read_by_name('Global.profiler.nstack', pyads.dint)

    # define a new stack class that can contain as many calls as were
    # actually performed - yes, we can do that with python :)
    class Stack(ctypes.Structure):
        _fields_ = [("calls", Call * nstack)]

    stack = plc.read_by_name('Global.profiler.stack', Stack)

    logging.debug('store measurement')
    pickle.dump(stack, open(os.path.join(dest, "callstack_{}".format(datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))), "wb"))

except pyads.ADSError as e:
    logging.error(e)
finally:
    plc.close()


