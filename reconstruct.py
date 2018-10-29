import os
import sys
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
from plcstack import Call, create_hash

class Stack(ctypes.Structure):
    _fields_ = [("calls", Call * 32000)]

parser = ArgumentParser("""triggers the measurement of a single profile and
stores the corresponding callstack on disk""")

parser.add_argument("-m", "--hashmap", help="hash map")
parser.add_argument("-c", "--callstack", help="callstack")
parser.add_argument("-d", "--dest", help="output directory ", default="./")
parser.add_argument("-g", "--graph", help="output directory ", action="store_true")
parser.add_argument("-t", "--cycletime_ms", help="plc cycletime in milliseconds", default=1)
parser.add_argument("-q", "--masquarade", help="hash fb and methodnames", action="store_true")
args = vars(parser.parse_args())

logging.basicConfig(level=logging.DEBUG)

hashmap_filepath = args['hashmap']
callstack_filepath = args['callstack']
dest = args['dest']

stack = pickle.load(open(callstack_filepath, 'rb'))
hm = pickle.load(open(hashmap_filepath, 'rb'))
hashes = {} # only needed for masquarade option

def extract_stack(stack, hashmap):
    nmainhash = 0
    lst = []
    for call in stack.calls:

        fb, method = hashmap.get(call.hash, (str(call.hash), str(call.hash)))

        if fb == 'MAIN':
            nmainhash += 1

        lst.append([fb, method, call.depth, call.starthi, call.startlo, call.endhi, call.endlo])

        if nmainhash >= 2:
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
                    dt_us = 0.1 * (((dend.endhi << 64) + (dend.endlo)) - ((dstart.starthi << 64) + (dstart.startlo)))
                    node_name = dstart.fb + '::' + dstart.method

                    if network.has_edge(node, node_name):
                        network[node][node_name]['attr_dict']['calls'] += 1
                        network[node][node_name]['attr_dict']['dt_us'] += [dt_us,]
                    else:
                        network.add_edge(node, node_name, attr_dict={'dt_us': [dt_us,], 'calls': 1})

                    logging.info((' '*depth) + '{}::{} ({} us)'.format(dstart.fb, dstart.method, dt_us))
                    build_graph(network, node_name, data, startid+1, endid-1, depth+1)

                    lastid = endid+1
                    break



lst = extract_stack(stack, hm)
data = pd.DataFrame(lst, columns=['fb', 'method', 'depth', 'starthi', 'startlo', 'endhi', 'endlo'])

n = networkx.DiGraph()
build_graph(n, 'root', data, 0, len(lst)-1)
logging.info('{} methods in stack'.format(int(len(lst)/2)))


def write_callgrind(network, f, node_dt, node='MAIN::MAIN', depth=0):
    global hashes
    ch = create_hash if args['masquarade'] else (lambda x,y,h: x + '::' + y if len(y) > 0 else x)

    if depth == 0:
        f.write('events: dt')

    # defaulting to cycle time 1 ms if something goes wront
    if node_dt < 0 and depth == 0:
        node_dt = 1000000000;
    elif node_dt < 0:
        raise Expection('node_dt < 0')

    node_fb, node_method = node.split('::')
    f.write('\nfl={}\n'.format(ch(node_fb, '', hashes)))
    f.write('fn={}\n'.format(ch(node_fb, node_method, hashes)))

    # get selfcost
    for _, n in enumerate(network.neighbors(node)):

        for dt_us in network.get_edge_data(node, n)['attr_dict']['dt_us']:
            node_dt -= int(dt_us*1000)


    f.write('{} {}\n'.format(1, node_dt))
    for i,n in enumerate(network.neighbors(node)):
        fb, method = n.split('::')

        calls = network.get_edge_data(node, n)['attr_dict']['calls']
        dts = network.get_edge_data(node, n)['attr_dict']['dt_us']

        for c in range(calls):
            f.write('cfl={}\n'.format(ch(fb, '', hashes)))
            f.write('cfn={}\n'.format(ch(fb, method, hashes)))
            f.write('calls={} {}\n'.format(1, 1))
            f.write('{} {}\n'.format(i, int(dts[c-1]*1000)))


    for i,n in enumerate(network.neighbors(node)):
        dt_us = network.get_edge_data(node, n)['attr_dict']['dt_us']
        write_callgrind(network, f, node_dt=int(max(dt_us)*1000), node=n, depth=depth+1)


with open(os.path.join(dest, 'callgrind.callgrind'), 'wt') as f:
    write_callgrind(n, f, int(args['cycletime_ms'] * 1000000))

if args['graph']:
    import matplotlib.pyplot as plt
    networkx.draw(n, with_labels=True)
    plt.show()