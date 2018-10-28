import os
import re
import logging
import time
import datetime
from argparse import ArgumentParser
import pyads
import ctypes
import pandas
import pickle
import networkx
import pandas as pd
from plcstack import Call

class Stack(ctypes.Structure):
    _fields_ = [("calls", Call * 32000)]

parser = ArgumentParser("""triggers the measurement of a single profile and
stores the corresponding callstack on disk""")

parser.add_argument("-m", "--hashmap", help="hash map")
parser.add_argument("-c", "--callstack", help="callstack")
parser.add_argument("-d", "--dest", help="output directory ", default="./")
parser.add_argument("-g", "--graph", help="output directory ", default=False, action="store_true")
args = vars(parser.parse_args())

logging.basicConfig(filename='output.log', level=logging.DEBUG)

hashmap_filepath = args['hashmap']
callstack_filepath = args['callstack']
dest = args['dest']

hm = pickle.load(open(hashmap_filepath, 'rb'))
stack = pickle.load(open(callstack_filepath, 'rb'))


def extract_stack(stack, hashmap):
    nmainhash = 0
    lst = []
    for call in stack.calls:


        fb, method = hashmap.get(call.hash, str(call.hash))

        if fb == 'MAIN':
            nmainhash += 1

        lst.append([fb, method, call.depth, call.starthi, call.startlo, call.endhi, call.endlo])

        if nmainhash >= 2:
            print(call.endhi, call.endlo)
            return lst

    return lst



def build_graph(network, node, data, sid, eid, depth=0):

    if eid <= sid:
        return;

    lastid = -1
    for startid,dstart in data.loc[sid:, :].iterrows():

        if startid >= lastid:

            for endid,dend in data.loc[startid+1:eid,:].iterrows():

                # todo bugfix bei pushMethod, dann können wir uns -1 sparen
                if dstart.fb == dend.fb and \
                   dstart.method == dend.method and \
                                startid != endid:

                    # FB node einfuegen
                    network.add_edge(dstart.method, node)
                    network.add_edge(dstart.method, dstart.fb)
                    dt_us = 0.1 * (((dend.endhi << 64) + (dend.endlo)) - ((dstart.starthi << 64) + (dstart.startlo)))

                    if sid == 0:
                        print(dend)
                        print(dstart)

                    logging.info((' '*depth) + '{}::{} ({} us)'.format(dstart.fb, dstart.method, dt_us))
                    build_graph(network, dstart.method, data, startid+1, endid-1, depth+1)

                    lastid = endid+1
                    break



lst = extract_stack(stack, hm)
data = pd.DataFrame(lst, columns=['fb', 'method', 'depth', 'starthi', 'startlo', 'endhi', 'endlo'])

n = networkx.DiGraph()
build_graph(n, 'root', data, 0, len(lst)-1)
logging.info('{} methods in stack'.format(int(len(lst)/2)))


if args['graph']:
    import matplotlib.pyplot as plt
    networkx.draw(n, with_labels=False)
    plt.show()